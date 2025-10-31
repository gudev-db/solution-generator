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
st.title("🚀 Gerador de Propostas para Editais de Inovação")
st.markdown("Encontre editais abertos e gere propostas completas no formato oficial")

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

    # Função para buscar editais abertos com Web Search
    def buscar_editais_abertos_web(palavras_chave, area_interesse, tipo_edital):
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.3
        )
        
        prompt = f'''
        Busque por EDITAIS ABERTOS E ATIVOS em todo o mundo para projetos de inovação, tecnologia e P&D.
        
        PALAVRAS-CHAVE: {palavras_chave}
        ÁREA DE INTERESSE: {area_interesse}
        TIPO DE EDITAL: {tipo_edital}
        
        Foque em encontrar editais ativos de:
        - Empresas de energia e utilities
        - Órgãos governamentais
        - Fundações de pesquisa
        - Programas de inovação
        - Agências de fomento
        - Empresas de tecnologia
        - Startups e venture capital
        
        Forneça informações detalhadas sobre:
        - Nome completo do edital
        - Organização responsável
        - Prazo de submissão (especificar se está aberto)
        - Valor disponível ou faixa de financiamento
        - Link oficial para mais informações
        - Áreas temáticas cobertas
        - Requisitos de elegibilidade
        - Contatos importantes
        
        Priorize editais com prazos em aberto e forneça informações atualizadas.
        '''
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            
            resultado = response.text
            
            # Adicionar informações das fontes se disponíveis
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    resultado += "\n\n---\n**FONTES E REFERÊNCIAS:**\n"
                    if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                        for i, chunk in enumerate(candidate.grounding_metadata.grounding_chunks[:5]):
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                resultado += f"\n{i+1}. {chunk.web.uri}"
            
            return resultado
            
        except Exception as e:
            return f"Erro na busca: {str(e)}"

    # Função para extrair texto de arquivos
    def extract_text_from_file(uploaded_file):
        text = ""
        file_type = uploaded_file.type
        
        if file_type == "application/pdf":
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
            text = str(uploaded_file.getvalue(), "utf-8")
        
        return text

    # Função para buscar editais específicos
    def buscar_editais_especificos(descricao_solucao, palavras_chave, area_atuacao, inovacao):
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.3
        )
        
        prompt = f'''
        Busque por EDITAIS ABERTOS adequados para esta solução específica:

        DESCRIÇÃO DA SOLUÇÃO: {descricao_solucao}
        ÁREA DE ATUAÇÃO: {area_atuacao}
        ELEMENTOS INOVADORES: {inovacao}
        PALAVRAS-CHAVE: {palavras_chave}

        Encontre editais ativos que se alinhem com esta solução.
        '''
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            return f"Erro na busca: {str(e)}"

    # Função para gerar proposta automática
    def gerar_proposta_automatica(desafio_edital):
        proposta_completa = {}
        
        # Analisar desafio e gerar solução
        prompt_analise = f'''
        ANALISE este desafio de edital e gere uma SOLUÇÃO INOVADORA completa:

        DESAFIO DO EDITAL:
        {desafio_edital}

        Gere uma solução tecnológica inovadora que inclua:
        1. Descrição técnica detalhada
        2. Elementos inovadores e diferenciais competitivos
        3. Tecnologias envolvidas (focar em IA, IoT, dados)
        4. Tipo de produto resultante
        5. Potencial de mercado e aplicação

        Retorne no formato:
        DESCRICAO_SOLUCAO: [descrição completa]
        INOVACAO: [aspectos inovadores]
        TECNOLOGIAS: [tecnologias utilizadas]
        TIPO_PRODUTO: [tipo de produto]
        POTENCIAL_MERCADO: [potencial de aplicação]

        Seja preciso, técnico e decidido no que será desenvolvido.
        Foque em implementações práticas que envolvam tecnologias avançadas.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_analise
        )
        
        resposta_analise = response.text
        linhas = resposta_analise.split('\n')
        
        dados_solucao = {}
        for linha in linhas:
            if 'DESCRICAO_SOLUCAO:' in linha:
                dados_solucao['descricao_solucao'] = linha.split('DESCRICAO_SOLUCAO:')[1].strip()
            elif 'INOVACAO:' in linha:
                dados_solucao['aspectos_inovativos'] = linha.split('INOVACAO:')[1].strip()
            elif 'TECNOLOGIAS:' in linha:
                dados_solucao['tecnologias_previstas'] = linha.split('TECNOLOGIAS:')[1].strip()
            elif 'TIPO_PRODUTO:' in linha:
                dados_solucao['tipo_produto'] = linha.split('TIPO_PRODUTO:')[1].strip()
            elif 'POTENCIAL_MERCADO:' in linha:
                dados_solucao['potencial_mercado'] = linha.split('POTENCIAL_MERCADO:')[1].strip()
        
        if not dados_solucao.get('descricao_solucao'):
            dados_solucao['descricao_solucao'] = resposta_analise
        
        # Preencher dados padrão
        dados_solucao.update({
            'area_atuacao': "Tecnologia e Inovação",
            'complexidade': "Alta",
            'tamanho_equipe': "8",
            'maturidade_tecnologica': "Protótipo Avançado",
            'trl_inicial': "TRL4",
            'trl_final': "TRL7",
            'propriedade_intelectual': "Potencial para patente devido aos aspectos inovadores",
            'estado_desenvolvimento': "Conceito validado"
        })
        
        # Gerar cada item do formulário
        prompt_titulo = f'''
        Crie um TÍTULO criativo e impactante (máx 200 caracteres):

        DESAFIO: {desafio_edital}
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:500]}
        Retorne APENAS o título.
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_titulo
        )
        proposta_completa['titulo'] = response.text.strip()[:200]
        
        prompt_desafio = f'''
        Extraia informações do desafio:
        {desafio_edital}
        Retorne:
        CÓDIGO: [código ou EDITAL-2024-XXX]
        NOME: [nome resumido do desafio]
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_desafio
        )
        proposta_completa['desafio_info'] = response.text
        
        prompt_duracao = f'''
        Estime duração realista em MESES:
        DESAFIO: {desafio_edital[:300]}
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:300]}
        Retorne APENAS o número.
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_duracao
        )
        proposta_completa['duracao_meses'] = response.text.strip()
        
        prompt_orcamento = f'''
        Calcule orçamento REALISTA para projeto de inovação:
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:400]}
        DURAÇÃO: {proposta_completa['duracao_meses']} meses
        COMPLEXIDADE: Alta
        Retorne valores realistas no formato:
        TOTAL: [valor total]
        RH: [recursos humanos]
        MATERIAL_PERMANENTE: [equipamentos]
        MATERIAL_CONSUMO: [materiais]
        SERVICOS_TERCEIROS: [serviços]
        VIAGENS: [viagens]
        OUTROS: [outros custos]
        COMUNICACAO: [comunicação]
        STARTUPS: [parcerias]
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_orcamento
        )
        proposta_completa['orcamento'] = response.text
        
        proposta_completa['tecnologias'] = dados_solucao['tecnologias_previstas']
        proposta_completa['tipo_produto'] = dados_solucao['tipo_produto'][:255]
        
        prompt_alcance = f'''
        Determine alcance realista:
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:400]}
        POTENCIAL: {dados_solucao.get('potencial_mercado', '')}
        Retorne uma das opções:
        - Local - Na empresa/organização
        - Nacional - No setor brasileiro
        - Internacional - No setor mundial
        - Diversificado - Abrangência em mais de um setor
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_alcance
        )
        proposta_completa['alcance'] = response.text.strip()
        
        proposta_completa['trl'] = f"TRL_INICIAL: {dados_solucao['trl_inicial']}\nTRL_FINAL: {dados_solucao['trl_final']}"
        proposta_completa['propriedade_intelectual'] = dados_solucao['propriedade_intelectual'][:1000]
        proposta_completa['aspectos_inovativos'] = dados_solucao['aspectos_inovativos'][:1000]
        
        prompt_ambito = f'''
        Descreva o âmbito de aplicação detalhado:
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:500]}
        TECNOLOGIAS: {dados_solucao['tecnologias_previstas']}
        POTENCIAL: {dados_solucao.get('potencial_mercado', '')}
        Inclua setores beneficiados, usuários potenciais e impactos esperados.
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_ambito
        )
        proposta_completa['ambito_aplicacao'] = response.text
        
        return proposta_completa, dados_solucao

    # Função para gerar proposta manual
    def gerar_proposta_manual(desafio_edital, dados_solucao):
        proposta_completa = {}
        
        prompt_titulo = f'''
        Crie um TÍTULO (máx 200 caracteres):
        DESAFIO: {desafio_edital}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        Retorne APENAS o título.
        '''
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_titulo
        )
        proposta_completa['titulo'] = response.text.strip()[:200]
        
        proposta_completa.update({
            'desafio_info': f"CÓDIGO: EDITAL-2024-001\nNOME: {desafio_edital[:50]}...",
            'duracao_meses': "18",
            'orcamento': "TOTAL: 1200000\nRH: 600000\nMATERIAL_PERMANENTE: 300000\nMATERIAL_CONSUMO: 100000\nSERVICOS_TERCEIROS: 150000\nVIAGENS: 30000\nOUTROS: 15000\nCOMUNICACAO: 20000\nSTARTUPS: 0",
            'tecnologias': dados_solucao.get('tecnologias_previstas', 'Tecnologias a definir'),
            'tipo_produto': dados_solucao.get('tipo_produto', 'Sistema integrado')[:255],
            'alcance': "Nacional - No setor brasileiro",
            'trl': f"TRL_INICIAL: {dados_solucao.get('trl_inicial', 'TRL4')}\nTRL_FINAL: {dados_solucao.get('trl_final', 'TRL7')}",
            'propriedade_intelectual': dados_solucao.get('propriedade_intelectual', 'Potencial para registro de patente')[:1000],
            'aspectos_inovativos': dados_solucao.get('aspectos_inovativos', 'Solução inovadora')[:1000],
            'ambito_aplicacao': dados_solucao.get('descricao_solucao', 'Aplicação em múltiplos setores')
        })
        
        return proposta_completa

    # Função para salvar no MongoDB
    def salvar_no_mongo(proposta_completa, desafio_edital, tipo="automática"):
        if mongo_connected:
            documento = {
                "id": str(uuid.uuid4()),
                "titulo": proposta_completa.get('titulo', ''),
                "desafio": desafio_edital[:500],
                "proposta_completa": proposta_completa,
                "tipo_geracao": tipo,
                "data_criacao": datetime.now()
            }
            collection.insert_one(documento)
            return True
        return False

    # Abas principais
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Busca Web Editais", "🎯 Editais por Solução", "🤖 Gerar Automaticamente", "📝 Formulário Manual"])

    with tab1:
        st.header("🔍 Busca por Editais Abertos")
        st.markdown("Busque editais ativos em todo o mundo usando Web Search")
        
        with st.form("form_busca_web"):
            col1, col2 = st.columns(2)
            
            with col1:
                palavras_chave_web = st.text_input(
                    "Palavras-chave principais:",
                    placeholder="IA, energia sustentável, IoT, smart grid...",
                    value="editais abertos inovação tecnologia P&D"
                )
                
                area_interesse = st.selectbox(
                    "Área de Interesse:",
                    [
                        "Energia e Utilities", "Tecnologia da Informação", "Saúde", 
                        "Agricultura", "Mobilidade", "Meio Ambiente", "Indústria 4.0",
                        "Cidades Inteligentes", "Educação", "Finanças", "Outra"
                    ]
                )
            
            with col2:
                tipo_edital = st.selectbox(
                    "Tipo de Edital:",
                    [
                        "P&D e Inovação", "Startups e Scale-ups", "Projetos Tecnológicos",
                        "Pesquisa Científica", "Desenvolvimento Sustentável", 
                        "Digital Transformation", "Todos os tipos"
                    ]
                )
                
                st.markdown("**Configurações de Busca:**")
                buscar_internacional = st.checkbox("Incluir editais internacionais", value=True)
                apenas_abertos = st.checkbox("Apenas editais com prazos abertos", value=True)
            
            submitted_web = st.form_submit_button("🌐 Buscar Editais na Web", type="primary")
        
        if submitted_web and gemini_api_key:
            with st.spinner("🔍 Buscando editais abertos na web..."):
                # Adicionar filtros à busca
                filtros = ""
                if apenas_abertos:
                    filtros += " com prazos em aberto"
                if buscar_internacional:
                    filtros += " incluindo oportunidades internacionais"
                
                resultado_busca = buscar_editais_abertos_web(
                    palavras_chave_web, 
                    area_interesse, 
                    tipo_edital + filtros
                )
                
                st.success("✅ Busca web concluída!")
                st.subheader("📋 Editais Abertos Encontrados")
                st.markdown(resultado_busca)
                
                # Estatísticas rápidas
                if "edital" in resultado_busca.lower():
                    st.sidebar.success("🎯 Editais encontrados com sucesso!")
                else:
                    st.sidebar.warning("⚠️ Tente ajustar os termos de busca")

    with tab2:
        st.header("🎯 Buscar Editais por Solução")
        st.markdown("Encontre editais específicos para sua solução")
        
        with st.form("form_busca_especifica"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_solucao = st.text_input("Nome da Solução:", placeholder="Sistema de monitoramento inteligente")
                area_solucao = st.selectbox("Área de Aplicação:", [
                    "Energia", "Tecnologia", "Saúde", "Educação", "Agricultura", 
                    "Mobilidade", "Meio Ambiente", "Indústria", "Outra"
                ])
                problema_resolve = st.text_area("Problema que Resolve:", placeholder="Descreva o problema abordado")
            
            with col2:
                como_funciona = st.text_area("Como Funciona:", placeholder="Explique o funcionamento")
                inovacao_solucao = st.text_area("Elementos Inovadores:", placeholder="Aspectos inovadores")
                beneficios = st.text_area("Benefícios Esperados:", placeholder="Impactos e benefícios")
            
            palavras_chave_busca = st.text_input("Palavras-chave:", "inovação, tecnologia, IA, sustentabilidade")
            
            submitted_busca = st.form_submit_button("🎯 Buscar Editais Específicos", type="primary")
        
        if submitted_busca and gemini_api_key:
            with st.spinner("Buscando editais para sua solução..."):
                descricao_completa = f"""
                NOME: {nome_solucao}
                ÁREA: {area_solucao}
                PROBLEMA: {problema_resolve}
                FUNCIONAMENTO: {como_funciona}
                INOVAÇÃO: {inovacao_solucao}
                BENEFÍCIOS: {beneficios}
                """
                
                resultado_busca = buscar_editais_especificos(
                    descricao_completa, 
                    palavras_chave_busca, 
                    area_solucao, 
                    inovacao_solucao
                )
                
                st.success("✅ Busca concluída!")
                st.subheader("📋 Editais Recomendados")
                st.markdown(resultado_busca)

    with tab3:
        st.header("🤖 Gerar Proposta Automaticamente")
        st.markdown("**Cole o desafio do edital e gere uma proposta completa automaticamente**")
        
        with st.form("form_auto"):
            desafio_edital = st.text_area(
                "Desafio do Edital:",
                height=200,
                placeholder="Cole aqui o texto completo do desafio do edital...\n\nExemplo: Desenvolvimento de sistema de monitoramento preditivo para infraestrutura crítica utilizando inteligência artificial e IoT..."
            )
            
            submitted_auto = st.form_submit_button("🚀 Gerar Proposta Automática", type="primary")
        
        if submitted_auto and gemini_api_key:
            if not desafio_edital.strip():
                st.error("Por favor, cole o desafio do edital.")
                st.stop()
            
            with st.spinner("🤖 Analisando desafio e gerando solução inovadora..."):
                proposta_completa, dados_solucao = gerar_proposta_automatica(desafio_edital)
                
                st.success("✅ Proposta gerada automaticamente!")
                
                # Exibir resumo
                st.subheader("💡 Solução Proposta")
                st.info(f"**Título:** {proposta_completa.get('titulo', '')}")
                st.write(f"**Descrição:** {dados_solucao.get('descricao_solucao', '')}")
                
                # Exibir proposta completa
                st.subheader("📋 Proposta Completa")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Título", proposta_completa.get('titulo', ''))
                    st.metric("Duração", f"{proposta_completa.get('duracao_meses', '')} meses")
                    st.metric("Alcance", proposta_completa.get('alcance', ''))
                
                with col2:
                    st.metric("TRL Inicial", proposta_completa.get('trl', '').split('\n')[0].replace('TRL_INICIAL: ', ''))
                    st.metric("TRL Final", proposta_completa.get('trl', '').split('\n')[1].replace('TRL_FINAL: ', ''))
                    st.metric("Tipo de Produto", proposta_completa.get('tipo_produto', ''))
                
                # Tecnologias e Inovação
                st.subheader("🔧 Tecnologias e Inovação")
                col3, col4 = st.columns(2)
                
                with col3:
                    st.write("**Tecnologias Utilizadas:**")
                    st.write(proposta_completa.get('tecnologias', ''))
                
                with col4:
                    st.write("**Aspectos Inovativos:**")
                    st.write(proposta_completa.get('aspectos_inovativos', ''))
                
                # Orçamento
                st.subheader("💰 Orçamento Detalhado")
                orcamento_texto = proposta_completa.get('orcamento', '')
                linhas_orcamento = orcamento_texto.split('\n')
                for linha in linhas_orcamento:
                    if ':' in linha:
                        chave, valor = linha.split(':', 1)
                        st.metric(label=chave.strip(), value=f"R$ {valor.strip()}")
                
                # Download
                proposta_completa_texto = f"""
                PROPOSTA PARA EDITAL - GERADA AUTOMATICAMENTE
                ============================================
                
                TÍTULO: {proposta_completa.get('titulo', '')}
                
                DESAFIO: {desafio_edital[:1000]}
                
                SOLUÇÃO: {dados_solucao.get('descricao_solucao', '')}
                
                INFORMAÇÕES:
                - Duração: {proposta_completa.get('duracao_meses', '')} meses
                - Alcance: {proposta_completa.get('alcance', '')}
                - TRL: {proposta_completa.get('trl', '')}
                
                ORÇAMENTO:
                {proposta_completa.get('orcamento', '')}
                
                TECNOLOGIAS: {proposta_completa.get('tecnologias', '')}
                INOVAÇÃO: {proposta_completa.get('aspectos_inovativos', '')}
                
                ÂMBITO DE APLICAÇÃO:
                {proposta_completa.get('ambito_aplicacao', '')}
                """
                
                st.download_button(
                    label="📥 Download da Proposta",
                    data=proposta_completa_texto,
                    file_name=f"proposta_edital_auto_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
                
                if salvar_no_mongo(proposta_completa, desafio_edital, "automática"):
                    st.sidebar.success("✅ Proposta salva!")

    with tab4:
        st.header("📝 Formulário Manual")
        st.markdown("Preencha os dados para gerar uma proposta personalizada")
        
        with st.form("form_manual"):
            st.subheader("Desafio do Edital")
            desafio_edital = st.text_area(
                "Desafio específico:",
                height=150,
                placeholder="Cole o desafio do edital..."
            )
            
            st.subheader("Solução Proposta")
            col1, col2 = st.columns(2)
            
            with col1:
                descricao_solucao = st.text_area(
                    "Descrição da solução:",
                    height=120,
                    placeholder="Descreva sua solução..."
                )
                
                aspectos_inovativos = st.text_area(
                    "Aspectos inovativos:",
                    height=100,
                    placeholder="O que tem de inovador..."
                )
                
                tecnologias_previstas = st.text_area(
                    "Tecnologias:",
                    height=80,
                    placeholder="Tecnologias utilizadas..."
                )
            
            with col2:
                tipo_produto = st.text_input(
                    "Tipo de produto:",
                    placeholder="Software, hardware, sistema..."
                )
                
                trl_inicial = st.selectbox(
                    "TRL Inicial:",
                    ["TRL1", "TRL2", "TRL3", "TRL4", "TRL5", "TRL6", "TRL7", "TRL8", "TRL9"],
                    index=3
                )
                
                trl_final = st.selectbox(
                    "TRL Final:",
                    ["TRL1", "TRL2", "TRL3", "TRL4", "TRL5", "TRL6", "TRL7", "TRL8", "TRL9"],
                    index=6
                )
            
            submitted_manual = st.form_submit_button("📝 Gerar Proposta Manual", type="primary")
        
        if submitted_manual and gemini_api_key:
            if not desafio_edital.strip():
                st.error("Por favor, insira o desafio do edital.")
                st.stop()
            
            dados_solucao = {
                'descricao_solucao': descricao_solucao,
                'aspectos_inovativos': aspectos_inovativos,
                'tecnologias_previstas': tecnologias_previstas,
                'tipo_produto': tipo_produto,
                'trl_inicial': trl_inicial,
                'trl_final': trl_final,
                'propriedade_intelectual': "A ser definido conforme desenvolvimento"
            }
            
            with st.spinner("Gerando proposta manual..."):
                proposta_completa = gerar_proposta_manual(desafio_edital, dados_solucao)
                
                st.success("✅ Proposta manual gerada!")
                
                # Exibir resultados
                st.subheader("📋 Proposta Gerada")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"**Título:** {proposta_completa.get('titulo', '')}")
                    st.info(f"**Duração:** {proposta_completa.get('duracao_meses', '')} meses")
                    st.info(f"**Alcance:** {proposta_completa.get('alcance', '')}")
                
                with col2:
                    st.info(f"**TRL:** {proposta_completa.get('trl', '')}")
                    st.info(f"**Produto:** {proposta_completa.get('tipo_produto', '')}")
                
                # Download
                proposta_texto = f"""
                PROPOSTA PARA EDITAL - FORMULÁRIO MANUAL
                =======================================
                
                TÍTULO: {proposta_completa.get('titulo', '')}
                
                DESAFIO: {desafio_edital}
                
                SOLUÇÃO: {descricao_solucao}
                
                INFORMAÇÕES:
                - Duração: {proposta_completa.get('duracao_meses', '')} meses
                - Alcance: {proposta_completa.get('alcance', '')}
                - TRL: {proposta_completa.get('trl', '')}
                - Produto: {proposta_completa.get('tipo_produto', '')}
                
                TECNOLOGIAS: {tecnologias_previstas}
                INOVAÇÃO: {aspectos_inovativos}
                """
                
                st.download_button(
                    label="📥 Download Proposta Manual",
                    data=proposta_texto,
                    file_name=f"proposta_edital_manual_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain"
                )
                
                if salvar_no_mongo(proposta_completa, desafio_edital, "manual"):
                    st.sidebar.success("✅ Proposta salva!")

elif not gemini_api_key:
    st.warning("⚠️ Por favor, insira uma API Key válida do Gemini.")

else:
    st.info("🔑 Para começar, insira sua API Key do Gemini acima.")

# Rodapé
st.divider()
st.caption("🚀 Gerador de Propostas para Editais | Desenvolvido para inovação e tecnologia")
