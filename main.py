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
st.set_page_config(page_title="Gerador de Propostas CEMIG", page_icon="⚡", layout="wide")

# Título do aplicativo
st.title("⚡ Gerador de Propostas para Editais CEMIG - PEQuI 2024-2028")
st.markdown("Encontre editais da CEMIG e gere propostas completas seguindo o formato oficial")

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
            db = client_mongo['propostas_cemig']
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

    # Função para buscar editais CEMIG específicos
    def buscar_editais_cemig(descricao_solucao, palavras_chave, area_atuacao, inovacao):
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        config = types.GenerateContentConfig(
            tools=[grounding_tool],
            temperature=0.3
        )
        
        prompt = f'''
        Busque especificamente por EDITAIS ABERTOS DA CEMIG (Companhia Energética de Minas Gerais) 
        no programa PEQuI 2024-2028 que sejam adequados para esta solução:

        DESCRIÇÃO DA SOLUÇÃO: {descricao_solucao}
        ÁREA DE ATUAÇÃO: {area_atuacao}
        ELEMENTOS INOVADORES: {inovacao}
        PALAVRAS-CHAVE: {palavras_chave}

        Foque em encontrar:
        1. Editais ativos da CEMIG/PEQuI para 2024-2025
        2. Desafios específicos com códigos identificadores
        3. Prazos de submissão
        4. Requisitos específicos da CEMIG
        5. Links oficiais no site da CEMIG

        Priorize informações do site oficial da CEMIG: www.cemig.com.br
        '''
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            
            resultado = response.text
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    resultado += "\n\n---\n**FONTES E REFERÊNCIAS OFICIAIS:**\n"
                    if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                        for i, chunk in enumerate(candidate.grounding_metadata.grounding_chunks[:5]):
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                resultado += f"\n{i+1}. {chunk.web.uri}"
            
            return resultado
            
        except Exception as e:
            return f"Erro na busca: {str(e)}"

    # Função para gerar proposta específica para CEMIG
    def gerar_proposta_cemig_completa(desafio_cemig, dados_solucao):
        """Gera proposta completa no formato específico da CEMIG"""
        
        proposta_cemig = {}
        
        # 4. Título da proposta (máx 200 caracteres)
        prompt_titulo = f'''
        Com base no desafio da CEMIG e na solução proposta, crie um TÍTULO criativo e impactante 
        com NO MÁXIMO 200 CARACTERES.

        DESAFIO CEMIG:
        {desafio_cemig}

        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        INOVAÇÃO: {dados_solucao['aspectos_inovativos']}
        ÁREA: {dados_solucao['area_atuacao']}

        Retorne APENAS o título, sem formatação adicional.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_titulo
        )
        proposta_cemig['titulo'] = response.text.strip()[:200]
        
        # Extrair código e nome do desafio automaticamente
        prompt_desafio = f'''
        Analise este desafio da CEMIG e extraia:
        1. Código do desafio (se mencionado)
        2. Nome completo do desafio

        DESAFIO:
        {desafio_cemig}

        Retorne no formato:
        CÓDIGO: [código ou "A ser definido"]
        NOME: [nome do desafio]
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_desafio
        )
        proposta_cemig['desafio_info'] = response.text
        
        # 17. Tema estratégico
        temas_estrategicos = [
            "TE1: Modernização e Modicidade Tarifária",
            "TE2: Eletrificação da Economia e Eficiência Energética", 
            "TE3: Inovações para Transmissão e Distribuição e Novas Tecnologias de Suporte – Inteligência Artificial, Realidade Virtual e Aumentada e Blockchain",
            "TE4: Digitalização, Padrões, Interoperabilidade e Cibersegurança",
            "TE5: Eletricidade de Baixo Carbono",
            "TE6: Armazenamento de Energia", 
            "TE7: Hidrogênio",
            "A proposta não está alinhada a nenhum tema estratégico",
            "Outra"
        ]
        
        prompt_tema = f'''
        Analise a solução proposta e o desafio da CEMIG, e indique qual TEMA ESTRATÉGICO do PEQuI 2024-2028 melhor se aplica.

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        INOVAÇÃO: {dados_solucao['aspectos_inovativos']}
        
        Temas disponíveis:
        {chr(10).join(temas_estrategicos)}

        Retorne APENAS o código do tema (ex: "TE1", "TE2", etc)
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_tema
        )
        proposta_cemig['tema_estrategico'] = response.text.strip()
        
        # 18. Duração do projeto
        prompt_duracao = f'''
        Estime a duração realista em MESES para executar este projeto de P&D considerando:
        - Complexidade da solução: {dados_solucao['complexidade']}
        - TRL inicial/final: {dados_solucao['trl_inicial']} para {dados_solucao['trl_final']}
        - Escopo do desafio: {desafio_cemig[:500]}
        - Descrição da solução: {dados_solucao['descricao_solucao'][:500]}

        Para projetos de P&D na área de energia, a duração típica é de 12-36 meses.
        Retorne APENAS o número de meses (ex: "18")
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_duracao
        )
        proposta_cemig['duracao_meses'] = response.text.strip()
        
        # 19-27. Orçamento detalhado
        prompt_orcamento = f'''
        Calcule estimativas REALISTAS de custos para um projeto de P&D na área de energia elétrica:

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        DURAÇÃO: {proposta_cemig['duracao_meses']} meses
        COMPLEXIDADE: {dados_solucao['complexidade']}
        TAMANHO EQUIPE: {dados_solucao['tamanho_equipe']} pessoas
        TIPO PRODUTO: {dados_solucao['tipo_produto']}

        Forneça valores REALISTAS em R$ considerando:
        - Projetos CEMIG typically variam de R$ 500.000 a R$ 5.000.000
        - Distribuição típica: 40-60% RH, 20-30% equipamentos, 10-20% outros
        - Inclua contrapartidas

        Retorne APENAS os números no formato:
        TOTAL: [valor]
        RH: [valor]
        MATERIAL_PERMANENTE: [valor]
        MATERIAL_CONSUMO: [valor]
        SERVICOS_TERCEIROS: [valor]
        VIAGENS: [valor]
        OUTROS: [valor]
        COMUNICACAO: [valor]
        STARTUPS: [valor]
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_orcamento
        )
        proposta_cemig['orcamento'] = response.text
        
        # 28. Tecnologias utilizadas
        prompt_tecnologias = f'''
        Liste as principais tecnologias que serão utilizadas no desenvolvimento deste projeto de P&D:

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        FOCO TECNOLÓGICO: {dados_solucao['tecnologias_previstas']}

        Seja específico e técnico. Inclua tecnologias como:
        - IoT, IA, Machine Learning, Blockchain
        - Sensores, drones, robótica
        - Plataformas digitais, software específico
        - Materiais avançados, componentes elétricos
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_tecnologias
        )
        proposta_cemig['tecnologias'] = response.text
        
        # 29. Tipo de produto
        prompt_produto = f'''
        Especifique o tipo de produto que será desenvolvido (Software, Hardware, Planta piloto, Sistema, etc)
        em NO MÁXIMO 255 CARACTERES.

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}

        Seja específico sobre o produto final.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_produto
        )
        proposta_cemig['tipo_produto'] = response.text.strip()[:255]
        
        # 30. Alcance previsto
        alcance_opcoes = [
            "Local - Na empresa",
            "Nacional - No setor elétrico Brasileiro", 
            "Internacional - No setor elétrico Mundial",
            "Diversificado - Abrangência em mais de um setor"
        ]
        
        prompt_alcance = f'''
        Determine o alcance previsto realista da solução:

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        POTENCIAL: {dados_solucao['potencial_mercado']}

        Opções: {alcance_opcoes}

        Considere o potencial de aplicação no setor elétrico brasileiro.
        Retorne APENAS a opção completa.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_alcance
        )
        proposta_cemig['alcance'] = response.text.strip()
        
        # 31-32. TRL Inicial e Final
        trl_opcoes = ["TRL1", "TRL2", "TRL3", "TRL4", "TRL5", "TRL6", "TRL7", "TRL8", "TRL9"]
        
        prompt_trl = f'''
        Determine o TRL inicial realista e o TRL final esperado para esta solução:

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        ESTADO ATUAL: {dados_solucao['estado_desenvolvimento']}
        MATURIDADE: {dados_solucao['maturidade_tecnologica']}

        Para projetos CEMIG, TRL inicial típico: 3-5, TRL final: 6-8
        Retorne no formato:
        TRL_INICIAL: [valor]
        TRL_FINAL: [valor]
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_trl
        )
        proposta_cemig['trl'] = response.text
        
        # 33. Propriedade intelectual
        prompt_pi = f'''
        Com base na solução proposta, descreva aspectos de propriedade intelectual:

        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        INOVAÇÃO: {dados_solucao['aspectos_inovativos']}
        {dados_solucao['propriedade_intelectual']}

        Se não houver PI pré-existente, descreva o potencial para patentes ou registros.
        Limite: 1000 caracteres.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_pi
        )
        proposta_cemig['propriedade_intelectual'] = response.text.strip()[:1000]
        
        # 34. Aspectos inovativos
        prompt_inovacao = f'''
        Descreva os ASPECTOS INOVATIVOS da solução em NO MÁXIMO 1000 CARACTERES.
        Destaque o que diferencia da concorrência e do estado da arte.

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        DIFERENCIAIS: {dados_solucao['aspectos_inovativos']}

        Foque em inovação tecnológica e aplicabilidade no setor elétrico.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_inovacao
        )
        proposta_cemig['aspectos_inovativos'] = response.text.strip()[:1000]
        
        # 35. Âmbito de aplicação
        prompt_ambito = f'''
        Descreva o POTENCIAL DE ADOÇÃO E UTILIZAÇÃO da solução no setor elétrico, incluindo:
        - Extensão da aplicação
        - Segmentos beneficiados  
        - Setor econômico
        - Número potencial de usuários/consumidores
        - Benefícios gerados para a CEMIG e setor

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao']}
        MERCADO: {dados_solucao['potencial_mercado']}

        Seja específico sobre o impacto no setor elétrico.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_ambito
        )
        proposta_cemig['ambito_aplicacao'] = response.text
        
        return proposta_cemig

    # Função para salvar no MongoDB
    def salvar_no_mongo(proposta_cemig, desafio_cemig):
        if mongo_connected:
            documento = {
                "id": str(uuid.uuid4()),
                "titulo": proposta_cemig.get('titulo', ''),
                "desafio": desafio_cemig[:500],
                "proposta_completa": proposta_cemig,
                "data_criacao": datetime.now(),
                "tema_estrategico": proposta_cemig.get('tema_estrategico', ''),
                "duracao_meses": proposta_cemig.get('duracao_meses', ''),
                "tipo_produto": proposta_cemig.get('tipo_produto', '')
            }
            collection.insert_one(documento)
            return True
        return False

    # Abas separadas para cada funcionalidade
    tab1, tab2, tab3 = st.tabs(["🔍 Buscar Editais CEMIG", "📝 Gerar Proposta", "⚡ Formato CEMIG"])

    with tab1:
        st.header("🔍 Buscar Editais CEMIG")
        st.markdown("Encontre editais ativos da CEMIG alinhados com sua solução")
        
        with st.form("form_busca_cemig"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_solucao = st.text_input("Nome da Solução:", placeholder="Ex: Sistema IoT para Monitoramento de Subestações")
                area_solucao = st.selectbox("Área de Aplicação:", [
                    "Distribuição de Energia", "Transmissão", "Geração", "Eficiência Energética", 
                    "Smart Grid", "Digitalização", "Energias Renováveis", "Armazenamento", "Outra"
                ])
                problema_resolve = st.text_area("Problema que Resolve:", placeholder="Descreva o problema no setor elétrico que sua solução aborda")
            
            with col2:
                como_funciona = st.text_area("Como Funciona:", placeholder="Explique brevemente como sua solução funciona")
                inovacao_solucao = st.text_area("O que tem de Inovador:", placeholder="Descreva os aspectos inovadores para o setor elétrico")
                beneficios = st.text_area("Benefícios para CEMIG:", placeholder="Quais benefícios sua solução traz para a CEMIG")
            
            palavras_chave_busca = st.text_input("Palavras-chave para busca:", "CEMIG, PEQuI, P&D, energia elétrica, inovação")
            
            submitted_busca = st.form_submit_button("🔍 Buscar Editais CEMIG", type="primary")
        
        if submitted_busca and gemini_api_key:
            with st.spinner("Buscando editais ativos da CEMIG..."):
                descricao_completa = f"""
                NOME: {nome_solucao}
                ÁREA: {area_solucao}
                PROBLEMA RESOLVIDO: {problema_resolve}
                COMO FUNCIONA: {como_funciona}
                INOVAÇÃO: {inovacao_solucao}
                BENEFÍCIOS CEMIG: {beneficios}
                """
                
                resultado_busca = buscar_editais_cemig(
                    descricao_completa, 
                    palavras_chave_busca, 
                    area_solucao, 
                    inovacao_solucao
                )
                
                st.success("✅ Busca de editais CEMIG concluída!")
                st.subheader("📋 Editais CEMIG Encontrados")
                st.markdown(resultado_busca)

    with tab2:
        st.header("📝 Gerar Proposta para Edital")
        st.markdown("Faça upload de um edital específico para gerar uma proposta completa")
        
        with st.form("form_gerar_proposta"):
            uploaded_file = st.file_uploader("Faça upload do edital (PDF, DOCX ou TXT):", 
                                            type=["pdf", "docx", "txt"])
            
            area_atuacao = st.selectbox("Área de Atuação Principal:", [
                "Distribuição de Energia", "Transmissão", "Geração", "Eficiência Energética", 
                "Smart Grid", "Digitalização", "Energias Renováveis", "Armazenamento", "Outra"
            ])
            
            palavras_chave = st.text_area("Palavras-chave (separadas por vírgula):", 
                                         "inovação, tecnologia, eficiência energética, smart grid, digitalização")
            
            diretrizes_usuario = st.text_area("Diretrizes ou Ideias Preliminares:", 
                                             "Ex: Focar em soluções de IoT para monitoramento remoto. Incluir parceria com universidades.")
            
            texto_manual = st.text_area("Ou cole o texto do edital manualmente:", height=200)
            
            submitted_proposta = st.form_submit_button("🚀 Gerar Proposta Completa", type="primary")
        
        if submitted_proposta and gemini_api_key:
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
            
            # [Código existente para geração de proposta padrão...]
            # (Manter o código existente da tab2)

    with tab3:
        st.header("⚡ Formulário CEMIG - PEQuI 2024-2028")
        st.markdown("Preencha os dados da sua solução para gerar uma proposta no formato oficial da CEMIG")
        
        with st.form("form_cemig"):
            st.subheader("Desafio CEMIG")
            desafio_cemig = st.text_area(
                "Cole aqui o texto do desafio específico da CEMIG:",
                height=150,
                placeholder="Ex: Desenvolvimento de sistema de monitoramento inteligente para subestações utilizando IoT e IA..."
            )
            
            st.subheader("Informações da Solução")
            col1, col2 = st.columns(2)
            
            with col1:
                descricao_solucao = st.text_area(
                    "Descrição detalhada da solução:",
                    height=120,
                    placeholder="Descreva como sua solução funciona, componentes, tecnologia..."
                )
                
                aspectos_inovativos = st.text_area(
                    "Aspectos inovativos (para item 34):",
                    height=100,
                    placeholder="O que torna sua solução inovadora em relação ao estado da arte..."
                )
                
                tecnologias_previstas = st.text_area(
                    "Tecnologias previstas:",
                    height=80,
                    placeholder= "IA, IoT, blockchain, sensores, plataformas digitais..."
                )
                
                tipo_produto = st.text_input(
                    "Tipo de produto (item 29):",
                    placeholder="Ex: Software de gestão, hardware IoT, planta piloto..."
                )
            
            with col2:
                estado_desenvolvimento = st.text_area(
                    "Estado atual de desenvolvimento:",
                    height=80,
                    placeholder="Conceito, protótipo, MVP, produto em teste..."
                )
                
                complexidade = st.select_slider(
                    "Complexidade do projeto:",
                    options=["Baixa", "Média", "Alta", "Muito Alta"]
                )
                
                tamanho_equipe = st.slider(
                    "Tamanho estimado da equipe:",
                    min_value=1,
                    max_value=20,
                    value=5
                )
                
                maturidade_tecnologica = st.selectbox(
                    "Maturidade tecnológica atual:",
                    ["Conceito", "Protótipo Inicial", "Protótipo Avançado", "MVP", "Produto em Teste"]
                )
            
            st.subheader("Parâmetros Técnicos")
            col3, col4 = st.columns(2)
            
            with col3:
                trl_inicial = st.selectbox(
                    "TRL Inicial (item 31):",
                    ["TRL1", "TRL2", "TRL3", "TRL4", "TRL5", "TRL6", "TRL7", "TRL8", "TRL9"],
                    index=2
                )
                
                trl_final = st.selectbox(
                    "TRL Final esperado (item 32):",
                    ["TRL1", "TRL2", "TRL3", "TRL4", "TRL5", "TRL6", "TRL7", "TRL8", "TRL9"],
                    index=6
                )
            
            with col4:
                propriedade_intelectual = st.text_area(
                    "Propriedade intelectual (item 33):",
                    height=80,
                    placeholder="Patentes existentes, registros, ou potencial para novos..."
                )
                
                potencial_mercado = st.text_area(
                    "Potencial de mercado:",
                    height=80,
                    placeholder="Estimativa de usuários, aplicabilidade, escalabilidade..."
                )
            
            submitted_cemig = st.form_submit_button("⚡ Gerar Proposta CEMIG", type="primary")
        
        if submitted_cemig and gemini_api_key:
            if not desafio_cemig.strip():
                st.error("Por favor, insira o texto do desafio da CEMIG.")
                st.stop()
            
            # Preparar dados da solução
            dados_solucao = {
                'descricao_solucao': descricao_solucao,
                'aspectos_inovativos': aspectos_inovativos,
                'area_atuacao': area_atuacao,
                'tecnologias_previstas': tecnologias_previstas,
                'tipo_produto': tipo_produto,
                'estado_desenvolvimento': estado_desenvolvimento,
                'complexidade': complexidade,
                'tamanho_equipe': tamanho_equipe,
                'maturidade_tecnologica': maturidade_tecnologica,
                'trl_inicial': trl_inicial,
                'trl_final': trl_final,
                'propriedade_intelectual': propriedade_intelectual,
                'potencial_mercado': potencial_mercado
            }
            
            with st.spinner("Gerando proposta no formato CEMIG..."):
                proposta_cemig = gerar_proposta_cemig_completa(desafio_cemig, dados_solucao)
                
                st.success("✅ Proposta CEMIG gerada com sucesso!")
                
                # Exibir resultados em formato organizado
                st.subheader("📋 Proposta CEMIG - PEQuI 2024-2028")
                
                # Criar abas para cada seção
                tabs_cemig = st.tabs([
                    "4. Título", "15-16. Desafio", "17. Tema", "18. Duração", 
                    "19-27. Orçamento", "28. Tecnologias", "29. Produto", "30. Alcance",
                    "31-32. TRL", "33. PI", "34. Inovação", "35. Âmbito"
                ])
                
                with tabs_cemig[0]:
                    st.info(f"**Título da Proposta:** {proposta_cemig.get('titulo', 'Não gerado')}")
                    st.code(proposta_cemig.get('titulo', ''), language=None)
                
                with tabs_cemig[1]:
                    st.info("**Informações do Desafio:**")
                    st.text_area("", proposta_cemig.get('desafio_info', ''), height=100)
                
                with tabs_cemig[2]:
                    st.info(f"**Tema Estratégico:** {proposta_cemig.get('tema_estrategico', 'Não definido')}")
                
                with tabs_cemig[3]:
                    st.info(f"**Duração do Projeto:** {proposta_cemig.get('duracao_meses', 'Não definido')} meses")
                
                with tabs_cemig[4]:
                    st.info("**Orçamento Detalhado:**")
                    orcamento_texto = proposta_cemig.get('orcamento', '')
                    # Formatar orçamento
                    linhas_orcamento = orcamento_texto.split('\n')
                    for linha in linhas_orcamento:
                        if ':' in linha:
                            chave, valor = linha.split(':', 1)
                            st.metric(label=chave.strip(), value=f"R$ {valor.strip()}")
                
                with tabs_cemig[5]:
                    st.info("**Tecnologias Utilizadas:**")
                    st.write(proposta_cemig.get('tecnologias', ''))
                
                with tabs_cemig[6]:
                    st.info(f"**Tipo de Produto:** {proposta_cemig.get('tipo_produto', '')}")
                
                with tabs_cemig[7]:
                    st.info(f"**Alcance Previsto:** {proposta_cemig.get('alcance', '')}")
                
                with tabs_cemig[8]:
                    st.info("**Níveis TRL:**")
                    st.write(proposta_cemig.get('trl', ''))
                
                with tabs_cemig[9]:
                    st.info("**Propriedade Intelectual:**")
                    st.text_area("", proposta_cemig.get('propriedade_intelectual', ''), height=150)
                
                with tabs_cemig[10]:
                    st.info("**Aspectos Inovativos:**")
                    st.text_area("", proposta_cemig.get('aspectos_inovativos', ''), height=150)
                
                with tabs_cemig[11]:
                    st.info("**Âmbito de Aplicação:**")
                    st.write(proposta_cemig.get('ambito_aplicacao', ''))
                
                # Botão de download
                proposta_completa_texto = f"""
                PROPOSTA CEMIG - PEQuI 2024-2028
                =================================
                
                4. TÍTULO DA PROPOSTA:
                {proposta_cemig.get('titulo', '')}
                
                15-16. DESAFIO:
                {proposta_cemig.get('desafio_info', '')}
                
                17. TEMA ESTRATÉGICO:
                {proposta_cemig.get('tema_estrategico', '')}
                
                18. DURAÇÃO DO PROJETO:
                {proposta_cemig.get('duracao_meses', '')} meses
                
                19-27. ORÇAMENTO:
                {proposta_cemig.get('orcamento', '')}
                
                28. TECNOLOGIAS UTILIZADAS:
                {proposta_cemig.get('tecnologias', '')}
                
                29. TIPO DE PRODUTO:
                {proposta_cemig.get('tipo_produto', '')}
                
                30. ALCANCE PREVISTO:
                {proposta_cemig.get('alcance', '')}
                
                31-32. TRL INICIAL/FINAL:
                {proposta_cemig.get('trl', '')}
                
                33. PROPRIEDADE INTELECTUAL:
                {proposta_cemig.get('propriedade_intelectual', '')}
                
                34. ASPECTOS INOVATIVOS:
                {proposta_cemig.get('aspectos_inovativos', '')}
                
                35. ÂMBITO DE APLICAÇÃO:
                {proposta_cemig.get('ambito_aplicacao', '')}
                """
                
                st.download_button(
                    label="📥 Download Proposta CEMIG",
                    data=proposta_completa_texto,
                    file_name=f"proposta_cemig_{proposta_cemig.get('titulo', 'proposta')[:30].replace(' ', '_')}.txt",
                    mime="text/plain"
                )
                
                # Salvar no MongoDB
                if salvar_no_mongo(proposta_cemig, desafio_cemig):
                    st.sidebar.success("✅ Proposta CEMIG salva no banco de dados!")

elif not gemini_api_key:
    st.warning("⚠️ Por favor, insira uma API Key válida do Gemini para gerar propostas.")

else:
    st.info("🔑 Para começar, insira sua API Key do Gemini na barra lateral.")

# Rodapé
st.divider()
st.caption("⚡ Gerador de Propostas CEMIG - Desenvolvido para o programa PEQuI 2024-2028")
