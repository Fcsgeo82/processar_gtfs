import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("0. Validar GTFS Entrada")
    st.markdown("Valida nomes de trips excepcionais, checa ausência de stop_times, valida shapes, etc.")
    
    # Parâmetros
    st.subheader("Parâmetros Específicos")
    
    # Deriva o valor padrão com base nos parâmetros globais
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    mes = st.session_state.mes_gtfs
    estudo = st.session_state.estudo_gtfs
    processar = st.session_state.gtfs_processar
    
    default_gtfs = f"{base_dados}/gtfs/{ano}/{processar}_{ano}-{mes}-{estudo}Q.zip"
    
    col1, col2 = st.columns(2)
    with col1:
        endereco_gtfs = st.text_input(
            "Caminho do GTFS (endereco_gtfs)",
            value=default_gtfs,
            help="Caminho completo ou modificado do ZIP a ser validado. Arquivo pode ser selecionado via upload na outra coluna.",
            key="t0_endereco_gtfs"
        )
        pasta_resultados = st.text_input(
            "Pasta de Resultados (PASTA_RESULTADOS)",
            value=f"{base_dados.replace('dados', 'resultados')}/validacoes_snapshot",
            help="Onde salvar o relatório de validação",
            key="t0_pasta_resultados"
        )
        
    with col2:
        uploaded_file = st.file_uploader(
            "Upload GTFS alternativo (Opcional)",
            type=['zip'],
            help="Faça o upload do GTFS para a aplicação se quiser sobrepor o text_input",
            key="t0_upload_gtfs"
        )
    
    if st.button("▶ Executar Script 0", key="btn_script_0"):
        # Se usuário fez upload, salvar temporariamente
        gtfs_path = endereco_gtfs
        temp_zip = None
        if uploaded_file is not None:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as f:
                f.write(uploaded_file.getbuffer())
                temp_zip = f.name
            gtfs_path = temp_zip
            st.info(f"Usando arquivo carregado: {uploaded_file.name}")
        
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "PASTA_RESULTADOS": pasta_resultados,
            "ano_gtfs": st.session_state.ano_gtfs,
            "mes_gtfs": st.session_state.mes_gtfs,
            "estudo_gtfs": st.session_state.estudo_gtfs,
            "gtfs_processar": st.session_state.gtfs_processar,
            "endereco_gtfs": gtfs_path
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "0_validar_gtfs_entrada.py"))
        run_script(script_path, config)
        
        # Limpar arquivo temporário se criado
        if temp_zip:
            try:
                os.remove(temp_zip)
            except:
                pass
