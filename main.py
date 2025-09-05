import streamlit as st
from google import genai
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
st.markdown("Transforme editais em propostas completas com planos de negócios, cronogramas e justificativas")

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
    def gerar_titulo_resumo(texto_edital, palavras_chave, diretrizes, area_atuacao):
        prompt = f'''
        Com base no edital fornecido, gere um TÍTULO CRIATIVO e um RESUMO EXECUTIVO para uma proposta de solução inovadora.

        TEXTO DO EDITAL:
        {texto_edital[:3000]}  # Limitando o tamanho para não exceder tokens

        PALAVRAS-CHAVE: {palavras_chave}
        DIRETRIZES: {diretrizes}
        ÁREA DE ATUAÇÃO: {area_atuacao}

        ESTRUTURE SUA RESPOSTA COM:
        TÍTULO: [Título criativo e alinhado ao edital]
        RESUMO EXECUTIVO: [Resumo de até 150 palavras explicando a solução proposta, seu diferencial inovador e benefícios esperados]
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_justificativa(texto_edital, palavras_chave, titulo_resumo):
        prompt = f'''
        Com base no edital e no título/resumo fornecidos, elabore uma JUSTIFICATIVA detalhada que explique:

        1. O problema a ser resolvido e sua relevância
        2. Por que a solução proposta é inovadora
        3. Diferenciais em relação a soluções existentes
        4. Alinhamento com as prioridades do edital

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        PALAVRAS-CHAVE: {palavras_chave}
        TÍTULO E RESUMO DA PROPOSTA: {titulo_resumo}

        Forneça uma justificativa técnica convincente com argumentos sólidos.
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_objetivos_metodologia(texto_edital, palavras_chave, conteudo_anterior):
        prompt = f'''
        Com base no edital e no conteúdo já desenvolvido, elabore os OBJETIVOS e a METODOLOGIA da proposta:

        OBJETIVOS:
        - Objetivo geral [1 objetivo principal]
        - Objetivos específicos [3-5 objetivos mensuráveis]

        METODOLOGIA:
        - Descrição detalhada da solução proposta
        - Métodos, técnicas e abordagens
        - Fluxo de desenvolvimento e implementação

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        PALAVRAS-CHAVE: {palavras_chave}
        CONTEÚDO JÁ DESENVOLVIDO: {conteudo_anterior}

        Forneça objetivos claros e uma metodologia bem estruturada.
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_cronograma(texto_edital, palavras_chave, conteudo_anterior):
        prompt = f'''
        Com base no edital e no conteúdo já desenvolvido, elabore um CRONOGRAMA DE IMPLEMENTAÇÃO detalhado:

        ESTRUTURE O CRONOGRAMA EM FASES:
        1. Pré-implantação (preparação, planejamento)
        2. Implantação (desenvolvimento, execução)
        3. Pós-implantação (testes, ajustes, operação)

        Para cada fase, inclua:
        - Atividades principais
        - Marcos e entregáveis
        - Duração estimada (semanas/meses)

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        PALAVRAS-CHAVE: {palavras_chave}
        CONTEÚDO JÁ DESENVOLVIDO: {conteudo_anterior}

        Forneça um cronograma realista e bem estruturado.
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_plano_negocios(texto_edital, palavras_chave, conteudo_anterior):
        prompt = f'''
        Com base no edital e no conteúdo já desenvolvido, elabore um PLANO DE NEGÓCIOS:

        ESTRUTURE O PLANO DE NEGÓCIOS COM:
        1. Modelo de negócio proposto
        2. Análise de mercado e concorrência
        3. Projeção financeira (investimento, custos, receitas)
        4. Estratégia de sustentabilidade

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        PALAVRAS-CHAVE: {palavras_chave}
        CONTEÚDO JÁ DESENVOLVIDO: {conteudo_anterior}

        Forneça um plano de negócios realista e bem fundamentado.
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_recursos_impactos(texto_edital, palavras_chave, conteudo_anterior):
        prompt = f'''
        Com base no edital e no conteúdo já desenvolvido, elabore a seção de RECURSOS NECESSÁRIOS e IMPACTOS ESPERADOS:

        RECURSOS NECESSÁRIOS:
        - Recursos humanos (equipe, competências)
        - Infraestrutura e equipamentos
        - Tecnologias e ferramentas
        - Parcerias estratégicas

        IMPACTOS ESPERADOS:
        - Impactos técnicos, econômicos e sociais
        - Benefícios para os stakeholders
        - Potencial de escalabilidade e replicabilidade

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        PALAVRAS-CHAVE: {palavras_chave}
        CONTEÚDO JÁ DESENVOLVIDO: {conteudo_anterior}

        Forneça uma descrição completa dos recursos necessários e impactos esperados.
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

    def gerar_conclusao(texto_edital, palavras_chave, conteudo_anterior):
        prompt = f'''
        Com base no edital e no conteúdo já desenvolvido, elabore uma CONCLUSÃO persuasiva:

        A conclusão deve:
        - Sintetizar os pontos principais da proposta
        - Reafirmar o potencial de sucesso e inovação
        - Destacar os benefícios e impactos esperados
        - Finalizar com uma chamada para ação convincente

        TEXTO DO EDITAL:
        {texto_edital[:3000]}

        PALAVRAS-CHAVE: {palavras_chave}
        CONTEÚDO JÁ DESENVOLVIDO: {conteudo_anterior}

        Forneça uma conclusão impactante e memorável.
        '''
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text

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

    # Área principal
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
            # Etapa 1: Título e Resumo
            st.write("🎯 Gerando título e resumo executivo...")
            titulo_resumo = gerar_titulo_resumo(texto_edital, palavras_chave, diretrizes_usuario, area_atuacao)
            todas_etapas['titulo_resumo'] = titulo_resumo
            
            # Extrair título para usar no nome do documento
            titulo_match = re.search(r'TÍTULO:\s*(.+)', titulo_resumo, re.IGNORECASE)
            titulo_proposta = titulo_match.group(1).strip() if titulo_match else f"Proposta para Edital de Inovação em {area_atuacao}"
            
            # Etapa 2: Justificativa
            st.write("📝 Desenvolvendo justificativa e inovação...")
            justificativa = gerar_justificativa(texto_edital, palavras_chave, titulo_resumo)
            todas_etapas['justificativa'] = justificativa
            
            # Etapa 3: Objetivos e Metodologia
            st.write("🎯 Definindo objetivos e metodologia...")
            conteudo_anterior = f"{titulo_resumo}\n\n{justificativa}"
            objetivos_metodologia = gerar_objetivos_metodologia(texto_edital, palavras_chave, conteudo_anterior)
            todas_etapas['objetivos_metodologia'] = objetivos_metodologia
            
            # Etapa 4: Cronograma
            st.write("📅 Elaborando cronograma de implementação...")
            conteudo_anterior = f"{conteudo_anterior}\n\n{objetivos_metodologia}"
            cronograma = gerar_cronograma(texto_edital, palavras_chave, conteudo_anterior)
            todas_etapas['cronograma'] = cronograma
            
            # Etapa 5: Plano de Negócios
            st.write("💼 Desenvolvendo plano de negócios...")
            conteudo_anterior = f"{conteudo_anterior}\n\n{cronograma}"
            plano_negocios = gerar_plano_negocios(texto_edital, palavras_chave, conteudo_anterior)
            todas_etapas['plano_negocios'] = plano_negocios
            
            # Etapa 6: Recursos e Impactos
            st.write("🛠️ Especificando recursos necessários e impactos...")
            conteudo_anterior = f"{conteudo_anterior}\n\n{plano_negocios}"
            recursos_impactos = gerar_recursos_impactos(texto_edital, palavras_chave, conteudo_anterior)
            todas_etapas['recursos_impactos'] = recursos_impactos
            
            # Etapa 7: Conclusão
            st.write("🔚 Finalizando com conclusão persuasiva...")
            conteudo_anterior = f"{conteudo_anterior}\n\n{recursos_impactos}"
            conclusao = gerar_conclusao(texto_edital, palavras_chave, conteudo_anterior)
            todas_etapas['conclusao'] = conclusao
            
            status.update(label="Proposta completa gerada!", state="complete")
        
        # Montar proposta completa
        proposta_completa = f"""
        {todas_etapas['titulo_resumo']}
        
        ## JUSTIFICATIVA E INOVAÇÃO
        {todas_etapas['justificativa']}
        
        ## OBJETIVOS E METODOLOGIA
        {todas_etapas['objetivos_metodologia']}
        
        ## CRONOGRAMA DE IMPLEMENTAÇÃO
        {todas_etapas['cronograma']}
        
        ## PLANO DE NEGÓCIOS
        {todas_etapas['plano_negocios']}
        
        ## RECURSOS NECESSÁRIOS E IMPACTOS ESPERADOS
        {todas_etapas['recursos_impactos']}
        
        ## CONCLUSÃO
        {todas_etapas['conclusao']}
        """
        
        # Exibir resultados
        st.success("✅ Proposta gerada com sucesso!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Metadados da Proposta")
            st.info(f"**Título:** {titulo_proposta}")
            st.info(f"**Área de Atuação:** {area_atuacao}")
            st.info(f"**Palavras-chave:** {palavras_chave}")
            
            # Botão para copiar texto
            st.download_button(
                label="📥 Download da Proposta",
                data=proposta_completa,
                file_name=f"proposta_edital_{titulo_proposta.lower().replace(' ', '_')[:30]}.txt",
                mime="text/plain"
            )
        
        with col2:
            st.subheader("🎯 Diretrizes Aplicadas")
            st.success(f"**Área de Foco:** {area_atuacao}")
            st.success(f"**Palavras-chave:** {palavras_chave}")
            if diretrizes_usuario.strip():
                st.success(f"**Diretrizes:** {diretrizes_usuario}")
        
        st.divider()
        
        # Abas para visualizar cada seção
        tabs = st.tabs(["Título e Resumo", "Justificativa", "Objetivos e Metodologia", 
                       "Cronograma", "Plano de Negócios", "Recursos e Impactos", "Conclusão", "Proposta Completa"])
        
        with tabs[0]:
            st.markdown(todas_etapas['titulo_resumo'])
        with tabs[1]:
            st.markdown(todas_etapas['justificativa'])
        with tabs[2]:
            st.markdown(todas_etapas['objetivos_metodologia'])
        with tabs[3]:
            st.markdown(todas_etapas['cronograma'])
        with tabs[4]:
            st.markdown(todas_etapas['plano_negocios'])
        with tabs[5]:
            st.markdown(todas_etapas['recursos_impactos'])
        with tabs[6]:
            st.markdown(todas_etapas['conclusao'])
        with tabs[7]:
            st.markdown(proposta_completa)
        
        # Salvar no MongoDB se conectado
        if mongo_connected:
            if salvar_no_mongo(titulo_proposta, area_atuacao, palavras_chave, texto_edital, todas_etapas):
                st.sidebar.success("✅ Proposta salva no banco de dados!")
    
    elif not gemini_api_key:
        st.warning("⚠️ Por favor, insira uma API Key válida do Gemini para gerar propostas.")

else:
    st.info("🔑 Para começar, insira sua API Key do Gemini na barra lateral.")

# Rodapé
st.divider()
st.caption("🚀 Gerador de Propostas para Editais - Desenvolvido para transformar ideias inovadoras em projetos concretos")
