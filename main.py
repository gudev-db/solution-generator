import streamlit as st
from google import genai
from google.genai import types
import os
import uuid
from datetime import datetime
from pymongo import MongoClient
import tempfile
import PyPDF2
import docx
import re

# Configuração da página
st.set_page_config(page_title="Gerador de Propostas para Editais", page_icon="🚀", layout="wide")

# Título do aplicativo
st.title("🚀 Gerador de Propostas para Editais de Solução Inovadora")
st.markdown("Descreva sua solução e encontre editais alinhados para submeter sua proposta")

# Configuração do Gemini API
gemini_api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
if not gemini_api_key:
    gemini_api_key = st.text_input("Digite sua API Key do Gemini:", type="password")

if gemini_api_key:
    client = genai.Client(api_key=gemini_api_key)
    
    # Conexão com MongoDB (opcional)
    try:
        mongodb_uri = st.secrets.get("MONGODB_URI", os.getenv("MONGODB_URI"))
        if mongodb_uri:
            client_mongo = MongoClient(mongodb_uri)
            db = client_mongo['propostas_editais']
            collection = db['propostas_geradas']
            mongo_connected = True
        else:
            mongo_connected = False
    except:
        mongo_connected = False
        st.warning("Conexão com MongoDB não configurada. As propostas não serão salvas.")

    # Função para extrair texto de arquivos
    def extract_text_from_file(uploaded_file):
        text = ""
        file_type = uploaded_file.type
        
        if file_type == "application/pdf":
            # Processar PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                with open(tmp_file_path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            except Exception as e:
                st.error(f"Erro ao ler PDF: {e}")
            finally:
                os.unlink(tmp_file_path)
                
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Processar DOCX
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                doc = docx.Document(tmp_file_path)
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
            except Exception as e:
                st.error(f"Erro ao ler DOCX: {e}")
            finally:
                os.unlink(tmp_file_path)
                
        else:
            # Processar texto simples
            text = str(uploaded_file.getvalue(), "utf-8")
        
        return text

    # Função para buscar editais usando Web Search
    def buscar_editais_com_web_search(descricao_solucao, palavras_chave, area_atuacao, inovacao):
        # Configurar a ferramenta de busca do Google
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.3
        )
        
        prompt = f'''
        Com base na seguinte solução inovadora, busque informações sobre editais ativos ou recentes que sejam adequados para esta proposta:

        DESCRIÇÃO DA SOLUÇÃO: {descricao_solucao}
        ÁREA DE ATUAÇÃO: {area_atuacao}
        ELEMENTOS INOVADORES: {inovacao}
        PALAVRAS-CHAVE: {palavras_chave}

        Forneça informações sobre:
        1. Editais ativos ou recentes que se alinhem com esta solução
        2. Órgãos/governos/instituições que financiam este tipo de solução
        3. Prazos e requisitos importantes
        4. Links e fontes para mais informações

        Seja específico e prático, fornecendo informações atualizadas e relevantes.
        '''
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            
            # Extrair metadados de fundamentação se disponíveis
            resultado = response.text
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    # Adicionar informações sobre as fontes
                    resultado += "\n\n---\n**FONTES E REFERÊNCIAS:**\n"
                    if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                        for i, chunk in enumerate(candidate.grounding_metadata.grounding_chunks[:5]):
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                resultado += f"\n{i+1}. {chunk.web.uri}"
            
            return resultado
            
        except Exception as e:
            return f"Erro na busca: {str(e)}"

    # Função para salvar no MongoDB
    def salvar_no_mongo(titulo, area_atuacao, palavras_chave, texto_edital, todas_etapas):
        if mongo_connected:
            documento = {
                "id": str(uuid.uuid4()),
                "titulo": titulo,
                "area_atuacao": area_atuacao,
                "palavras_chave": palavras_chave,
                "texto_edital": texto_edital[:1000] + "..." if len(texto_edital) > 1000 else texto_edital,
                "proposta_completa": todas_etapas,
                "data_criacao": datetime.now()
            }
            collection.insert_one(documento)
            return True
        return False

    # Funções para cada etapa da proposta
    def gerar_titulo_resumo(texto_edital, palavras_chave, diretrizes, area_atuacao, descricao_solucao):
        prompt = f'''
        Com base no edital fornecido e na solução do usuário, gere um TÍTULO CRIATIVO e um RESUMO EXECUTIVO para uma proposta.

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        SOLUÇÃO DO USUÁRIO:
        {descricao_solucao}

        PALAVRAS-CHAVE: {palavras_chave}
        DIRETRIZES: {diretrizes}
        ÁREA DE ATUAÇÃO: {area_atuacao}

        ESTRUTURE SUA RESPOSTA COM:
        TÍTULO: [Título criativo e alinhado ao edital e à solução]
        RESUMO EXECUTIVO: [Resumo de até 150 palavras explicando a solução proposta, seu diferencial inovador e benefícios esperados]
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_justificativa(texto_edital, palavras_chave, titulo_resumo, descricao_solucao, inovacao):
        prompt = f'''
        Com base no edital, no título/resumo fornecidos e na solução do usuário, elabore uma JUSTIFICATIVA detalhada.

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        SOLUÇÃO DO USUÁRIO:
        {descricao_solucao}

        ELEMENTOS INOVADORES: {inovacao}
        PALAVRAS-CHAVE: {palavras_chave}
        TÍTULO E RESUMO DA PROPOSTA: {titulo_resumo}

        Forneça uma justificativa técnica convincente que destaque:
        1. O problema a ser resolvido e sua relevância
        2. Por que a solução proposta é inovadora
        3. Diferenciais em relação a soluções existentes
        4. Alinhamento com as prioridades do edital
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    # ... (outras funções de geração mantidas como antes)

    # Interface do usuário
    with st.sidebar:
        st.header("📋 Configurações da Proposta")
        
        # Upload do edital
        uploaded_file = st.file_uploader("Faça upload do edital (PDF, DOCX ou TXT):", 
                                        type=["pdf", "docx", "txt"])
        
        area_atuacao = st.selectbox("Área de Atuação Principal:", [
            "Tecnologia da Informação", "Saúde", "Educação", "Agronegócio", 
            "Energia", "Meio Ambiente", "Mobilidade Urbana", "Indústria 4.0",
            "Segurança", "Turismo", "Outra"
        ])
        
        if area_atuacao == "Outra":
            area_atuacao = st.text_input("Especifique a área de atuação:")
        
        palavras_chave = st.text_area("Palavras-chave (separadas por vírgula):", 
                                     "inovação, tecnologia, sustentabilidade, eficiência")
        
        diretrizes_usuario = st.text_area("Diretrizes ou Ideias Preliminares:", 
                                         "Ex: Focar em soluções de IoT para monitoramento remoto. Incluir parceria com universidades. Considerar baixo custo de implementação.")
        
        st.divider()
        
        # Opção para inserir texto manualmente
        texto_manual = st.text_area("Ou cole o texto do edital manualmente:", height=200)
        
        st.divider()
        gerar_proposta = st.button("🚀 Gerar Proposta Completa", type="primary", use_container_width=True)

    # Área principal - Descrição da Solução do Usuário
    st.header("💡 Descreva Sua Solução Inovadora")
    
    with st.expander("Preencha os detalhes da sua solução", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome_solucao = st.text_input("Nome da Solução:", placeholder="Ex: Sistema IoT de Monitoramento Agrícola")
            area_solucao = st.selectbox("Área de Aplicação:", [
                "Agricultura", "Saúde", "Educação", "Energia", "Meio Ambiente", 
                "Mobilidade", "Indústria", "Tecnologia", "Outra"
            ])
            problema_resolve = st.text_area("Problema que Resolve:", placeholder="Descreva o problema que sua solução aborda")
        
        with col2:
            como_funciona = st.text_area("Como Funciona:", placeholder="Explique brevemente como sua solução funciona")
            inovacao_solucao = st.text_area("O que tem de Inovador:", placeholder="Descreva os aspectos inovadores")
            beneficios = st.text_area("Benefícios e Impactos:", placeholder="Quais benefícios e impactos sua solução traz")
        
        # Botão para buscar editais alinhados
        buscar_editais = st.button("🔍 Buscar Editais Alinhados", type="secondary")

    # Processar busca de editais
    if buscar_editais and gemini_api_key:
        with st.spinner("Buscando editais alinhados com sua solução..."):
            descricao_completa = f"""
            NOME: {nome_solucao}
            ÁREA: {area_solucao}
            PROBLEMA RESOLVIDO: {problema_resolve}
            COMO FUNCIONA: {como_funciona}
            INOVAÇÃO: {inovacao_solucao}
            BENEFÍCIOS: {beneficios}
            """
            
            resultado_busca = buscar_editais_com_web_search(
                descricao_completa, 
                palavras_chave, 
                area_solucao, 
                inovacao_solucao
            )
            
            st.success("✅ Busca de editais concluída!")
            st.subheader("📋 Editais Encontrados")
            st.markdown(resultado_busca)

    # Restante do código para geração da proposta (mantido como antes)
    if gerar_proposta and gemini_api_key:
        # Obter texto do edital
        texto_edital = ""
        
        if uploaded_file is not None:
            with st.spinner("Processando arquivo do edital..."):
                texto_edital = extract_text_from_file(uploaded_file)
                if not texto_edital.strip():
                    st.error("Não foi possível extrair texto do arquivo. Tente outro formato ou use a opção de texto manual.")
                    st.stop()
        elif texto_manual.strip():
            texto_edital = texto_manual
        else:
            st.error("Por favor, faça upload de um edital ou cole o texto manualmente.")
            st.stop()
        
        # Gerar proposta em etapas
        todas_etapas = {}
        
        with st.status("Gerando proposta passo a passo...", expanded=True) as status:
            # Preparar descrição da solução do usuário
            descricao_solucao = f"""
            NOME: {nome_solucao}
            ÁREA: {area_solucao}
            PROBLEMA RESOLVIDO: {problema_resolve}
            COMO FUNCIONA: {como_funciona}
            INOVAÇÃO: {inovacao_solucao}
            BENEFÍCIOS: {beneficios}
            """
            
            # Etapa 1: Título e Resumo
            st.write("🎯 Gerando título e resumo executivo...")
            titulo_resumo = gerar_titulo_resumo(texto_edital, palavras_chave, diretrizes_usuario, area_atuacao, descricao_solucao)
            todas_etapas['titulo_resumo'] = titulo_resumo
            
            # Extrair título para usar no nome do documento
            titulo_match = re.search(r'TÍTULO:\s*(.+)', titulo_resumo, re.IGNORECASE)
            titulo_proposta = titulo_match.group(1).strip() if titulo_match else f"Proposta para Edital de Inovação em {area_atuacao}"
            
            # Etapa 2: Justificativa
            st.write("📝 Desenvolvendo justificativa e inovação...")
            justificativa = gerar_justificativa(texto_edital, palavras_chave, titulo_resumo, descricao_solucao, inovacao_solucao)
            todas_etapas['justificativa'] = justificativa
            
            # ... (continuar com as outras etapas)
            
            status.update(label="Proposta completa gerada!", state="complete")
        
        # Montar e exibir proposta completa
        st.success("✅ Proposta gerada com sucesso!")
        # ... (restante do código de exibição)

elif not gemini_api_key:
    st.warning("⚠️ Por favor, insira uma API Key válida do Gemini para gerar propostas.")

else:
    st.info("🔑 Para começar, insira sua API Key do Gemini na barra lateral.")

# Rodapé
st.divider()
st.caption("🚀 Gerador de Propostas para Editais - Desenvolvido para transformar ideias inovadoras em projetos concretos")
