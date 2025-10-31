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
st.markdown("Descreva o desafio da CEMIG e gere automaticamente uma solução completa no formato oficial")

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

    # Função para gerar proposta CEMIG completa apenas com o desafio
    def gerar_proposta_cemig_automatica(desafio_cemig):
        """Gera proposta completa automaticamente baseada apenas no desafio"""
        
        proposta_cemig = {}
        
        # Primeiro, analisar o desafio e gerar uma solução inovadora
        prompt_analise_desafio = f'''
        ANALISE este desafio da CEMIG e gere uma SOLUÇÃO INOVADORA completa:

        DESAFIO CEMIG:
        {desafio_cemig}

        Com base nisso, crie uma solução tecnológica inovadora para o setor elétrico que inclua:
        1. Descrição técnica detalhada da solução
        2. Elementos inovadores e diferenciais
        3. Tecnologias envolvidas
        4. Tipo de produto resultante
        5. Potencial de aplicação no setor elétrico

        Retorne no formato:
        DESCRICAO_SOLUCAO: [descrição completa]
        INOVACAO: [aspectos inovadores]
        TECNOLOGIAS: [tecnologias utilizadas]
        TIPO_PRODUTO: [tipo de produto]
        POTENCIAL_MERCADO: [potencial de aplicação]
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_analise_desafio
        )
        
        # Processar a resposta para extrair os componentes
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
        
        # Se não conseguiu extrair, usar a resposta completa
        if not dados_solucao.get('descricao_solucao'):
            dados_solucao['descricao_solucao'] = resposta_analise
        
        # Preencher dados padrão baseados na análise do desafio
        dados_solucao['area_atuacao'] = "Tecnologia para Setor Elétrico"
        dados_solucao['complexidade'] = "Alta"
        dados_solucao['tamanho_equipe'] = "8"
        dados_solucao['maturidade_tecnologica'] = "Protótipo Avançado"
        dados_solucao['trl_inicial'] = "TRL4"
        dados_solucao['trl_final'] = "TRL7"
        dados_solucao['propriedade_intelectual'] = "Potencial para patente devido aos aspectos inovadores da solução"
        dados_solucao['estado_desenvolvimento'] = "Conceito validado, pronto para desenvolvimento de protótipo"
        
        # Agora gerar cada item do formulário CEMIG
        
        # 4. Título da proposta (máx 200 caracteres)
        prompt_titulo = f'''
        Com base no desafio e solução, crie um TÍTULO criativo e impactante (máx 200 caracteres):

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:500]}

        Retorne APENAS o título.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_titulo
        )
        proposta_cemig['titulo'] = response.text.strip()[:200]
        
        # 15-16. Código e nome do desafio
        prompt_desafio = f'''
        Extraia informações do desafio CEMIG:

        {desafio_cemig}

        Se houver código, extraia. Caso contrário, sugira um código apropriado.
        Retorne:
        CÓDIGO: [código ou CEMIG-PEQ-2024-XXX]
        NOME: [nome resumido do desafio]
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_desafio
        )
        proposta_cemig['desafio_info'] = response.text
        
        # 17. Tema estratégico
        prompt_tema = f'''
        Analise o desafio e solução e indique o TEMA ESTRATÉGICO do PEQuI 2024-2028:

        DESAFIO: {desafio_cemig}
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:500]}

        Temas: TE1, TE2, TE3, TE4, TE5, TE6, TE7
        Retorne APENAS o código do tema (ex: "TE3").
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_tema
        )
        proposta_cemig['tema_estrategico'] = response.text.strip()
        
        # 18. Duração do projeto
        prompt_duracao = f'''
        Estime duração realista em MESES para este projeto de P&D:

        DESAFIO: {desafio_cemig[:300]}
        SOLUÇÃO: {dados_solucao['descricao_solucao'][:300]}
        COMPLEXIDADE: {dados_solucao['complexidade']}

        Para P&D no setor elétrico, considere 12-24 meses.
        Retorne APENAS o número.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_duracao
        )
        proposta_cemig['duracao_meses'] = response.text.strip()
        
        # 19-27. Orçamento detalhado
        prompt_orcamento = f'''
        Calcule orçamento REALISTA para projeto CEMIG:

        SOLUÇÃO: {dados_solucao['descricao_solucao'][:400]}
        DURAÇÃO: {proposta_cemig['duracao_meses']} meses
        COMPLEXIDADE: {dados_solucao['complexidade']}
        EQUIPE: {dados_solucao['tamanho_equipe']} pessoas

        Valores típicos CEMIG: R$ 500.000 - R$ 2.000.000
        Distribuição: 50% RH, 20% equipamentos, 15% serviços, 15% outros

        Retorne APENAS números no formato:
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
        proposta_cemig['tecnologias'] = dados_solucao['tecnologias_previstas']
        
        # 29. Tipo de produto
        proposta_cemig['tipo_produto'] = dados_solucao['tipo_produto'][:255]
        
        # 30. Alcance previsto
        prompt_alcance = f'''
        Determine alcance desta solução:

        SOLUÇÃO: {dados_solucao['descricao_solucao'][:400]}
        POTENCIAL: {dados_solucao['potencial_mercado']}

        Opções:
        - Local - Na empresa
        - Nacional - No setor elétrico Brasileiro  
        - Internacional - No setor elétrico Mundial
        - Diversificado - Abrangência em mais de um setor

        Retorne APENAS a opção completa.
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_alcance
        )
        proposta_cemig['alcance'] = response.text.strip()
        
        # 31-32. TRL Inicial e Final
        proposta_cemig['trl'] = f"TRL_INICIAL: {dados_solucao['trl_inicial']}\nTRL_FINAL: {dados_solucao['trl_final']}"
        
        # 33. Propriedade intelectual
        proposta_cemig['propriedade_intelectual'] = dados_solucao['propriedade_intelectual'][:1000]
        
        # 34. Aspectos inovativos
        proposta_cemig['aspectos_inovativos'] = dados_solucao['aspectos_inovativos'][:1000]
        
        # 35. Âmbito de aplicação
        prompt_ambito = f'''
        Descreva o âmbito de aplicação detalhado:

        SOLUÇÃO: {dados_solucao['descricao_solucao'][:500]}
        TECNOLOGIAS: {dados_solucao['tecnologias_previstas']}
        POTENCIAL: {dados_solucao['potencial_mercado']}

        Inclua:
        - Setores beneficiados
        - Número potencial de usuários
        - Impacto no setor elétrico
        - Benefícios para CEMIG
        '''
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_ambito
        )
        proposta_cemig['ambito_aplicacao'] = response.text
        
        return proposta_cemig, dados_solucao

    # Função para salvar no MongoDB
    def salvar_no_mongo(proposta_cemig, desafio_cemig):
        if mongo_connected:
            documento = {
                "id": str(uuid.uuid4()),
                "titulo": proposta_cemig.get('titulo', ''),
                "desafio": desafio_cemig[:500],
                "proposta_completa": proposta_cemig,
                "data_criacao": datetime.now(),
                "tema_estrategico": proposta_cemig.get('tema_estrategico', '')
            }
            collection.insert_one(documento)
            return True
        return False

    # Interface principal simplificada
    st.header("⚡ Gerador Automático de Propostas CEMIG")
    st.markdown("**Cole o desafio da CEMIG abaixo e gere automaticamente uma proposta completa**")

    with st.form("form_cemig_automatico"):
        desafio_cemig = st.text_area(
            "**Desafio da CEMIG:**",
            height=200,
            placeholder="Cole aqui o texto completo do desafio específico da CEMIG...\n\nExemplo: Desenvolvimento de sistema de monitoramento preditivo para ativos de distribuição utilizando inteligência artificial e IoT para prever falhas e otimizar manutenção..."
        )
        
        submitted = st.form_submit_button("🚀 Gerar Proposta Completa", type="primary")

    if submitted and gemini_api_key:
        if not desafio_cemig.strip():
            st.error("Por favor, cole o desafio da CEMIG.")
            st.stop()
        
        with st.spinner("🤖 Analisando o desafio e gerando solução inovadora..."):
            proposta_cemig, dados_solucao = gerar_proposta_cemig_automatica(desafio_cemig)
            
            st.success("✅ Proposta CEMIG gerada automaticamente!")
            
            # Exibir resumo da solução gerada
            st.subheader("💡 Solução Proposta (Gerada Automaticamente)")
            st.info(f"**Título:** {proposta_cemig.get('titulo', '')}")
            st.write(f"**Descrição:** {dados_solucao.get('descricao_solucao', '')}")
            st.write(f"**Inovação:** {dados_solucao.get('aspectos_inovativos', '')}")
            
            # Exibir proposta completa em formato organizado
            st.subheader("📋 Proposta CEMIG - PEQuI 2024-2028")
            
            # Criar abas para cada seção
            tabs_cemig = st.tabs([
                "4. Título", "15-16. Desafio", "17. Tema", "18. Duração", 
                "19-27. Orçamento", "28. Tecnologias", "29. Produto", "30. Alcance",
                "31-32. TRL", "33. PI", "34. Inovação", "35. Âmbito"
            ])
            
            with tabs_cemig[0]:
                st.info(f"**Título da Proposta:**")
                st.code(proposta_cemig.get('titulo', ''), language=None)
                st.metric("Caracteres", len(proposta_cemig.get('titulo', '')))
            
            with tabs_cemig[1]:
                st.info("**Informações do Desafio:**")
                st.text_area("", proposta_cemig.get('desafio_info', ''), height=100, key="desafio_info")
            
            with tabs_cemig[2]:
                tema = proposta_cemig.get('tema_estrategico', 'Não definido')
                st.info(f"**Tema Estratégico:** {tema}")
                if tema.startswith('TE'):
                    st.success(f"✅ Alinhado com {tema}")
            
            with tabs_cemig[3]:
                duracao = proposta_cemig.get('duracao_meses', 'Não definido')
                st.info(f"**Duração do Projeto:** {duracao} meses")
                st.metric("Duração Estimada", f"{duracao} meses")
            
            with tabs_cemig[4]:
                st.info("**Orçamento Detalhado:**")
                orcamento_texto = proposta_cemig.get('orcamento', '')
                linhas_orcamento = orcamento_texto.split('\n')
                for linha in linhas_orcamento:
                    if ':' in linha:
                        chave, valor = linha.split(':', 1)
                        valor_limpo = valor.strip()
                        if valor_limpo.replace(',', '').replace('.', '').isdigit():
                            st.metric(label=chave.strip(), value=f"R$ {valor_limpo}")
                        else:
                            st.write(f"**{chave.strip()}:** {valor_limpo}")
            
            with tabs_cemig[5]:
                st.info("**Tecnologias Utilizadas:**")
                tecnologias = proposta_cemig.get('tecnologias', '')
                st.write(tecnologias)
                # Destacar tecnologias chave
                tech_keywords = ['IA', 'IoT', 'blockchain', 'machine learning', 'cloud', 'sensor', 'digital']
                for keyword in tech_keywords:
                    if keyword.lower() in tecnologias.lower():
                        st.success(f"✅ {keyword.upper()} incluído")
            
            with tabs_cemig[6]:
                produto = proposta_cemig.get('tipo_produto', '')
                st.info(f"**Tipo de Produto:** {produto}")
                st.metric("Caracteres", len(produto))
            
            with tabs_cemig[7]:
                alcance = proposta_cemig.get('alcance', '')
                st.info(f"**Alcance Previsto:** {alcance}")
                if "Nacional" in alcance or "Internacional" in alcance:
                    st.success("🎯 Alto potencial de impacto")
            
            with tabs_cemig[8]:
                st.info("**Níveis TRL:**")
                trl_text = proposta_cemig.get('trl', '')
                st.write(trl_text)
                if "TRL4" in trl_text and "TRL7" in trl_text:
                    st.success("📈 Evolução tecnológica significativa")
            
            with tabs_cemig[9]:
                st.info("**Propriedade Intelectual:**")
                pi_text = proposta_cemig.get('propriedade_intelectual', '')
                st.text_area("", pi_text, height=150, key="pi")
                st.metric("Caracteres", len(pi_text))
            
            with tabs_cemig[10]:
                st.info("**Aspectos Inovativos:**")
                inovacao_text = proposta_cemig.get('aspectos_inovativos', '')
                st.text_area("", inovacao_text, height=150, key="inovacao")
                st.metric("Caracteres", len(inovacao_text))
            
            with tabs_cemig[11]:
                st.info("**Âmbito de Aplicação:**")
                ambito_text = proposta_cemig.get('ambito_aplicacao', '')
                st.write(ambito_text)
            
            # Botão de download
            proposta_completa_texto = f"""
            PROPOSTA CEMIG - PEQuI 2024-2028
            =================================
            Gerado automaticamente em {datetime.now().strftime("%d/%m/%Y %H:%M")}
            
            SOLUÇÃO GERADA AUTOMATICAMENTE:
            {dados_solucao.get('descricao_solucao', '')}
            
            INOVAÇÃO:
            {dados_solucao.get('aspectos_inovativos', '')}
            
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
                label="📥 Download da Proposta Completa",
                data=proposta_completa_texto,
                file_name=f"proposta_cemig_auto_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                type="primary"
            )
            
            # Salvar no MongoDB
            if salvar_no_mongo(proposta_cemig, desafio_cemig):
                st.sidebar.success("✅ Proposta salva no banco de dados!")

elif not gemini_api_key:
    st.warning("⚠️ Por favor, insira uma API Key válida do Gemini para gerar propostas.")

else:
    st.info("🔑 Para começar, insira sua API Key do Gemini acima.")

# Rodapé
st.divider()
st.caption("⚡ Gerador Automático de Propostas CEMIG - Desenvolvido para o programa PEQuI 2024-2028")
