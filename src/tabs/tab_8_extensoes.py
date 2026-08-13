import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("8. Gerar Extensões")
    st.markdown("Calcula a extensão em quilômetros para cada shape do GTFS.")
    
    modo = st.radio("Selecione o tipo de processamento", ["Padrão (Script 8)", "Formato Rio (Script 8.1)"], key="t8_modo")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    mes = st.session_state.mes_gtfs
    estudo = st.session_state.estudo_gtfs
    
    if "Padrão" in modo:
        default_gtfs = f"{base_dados}/gtfs/{ano}/gtfs_rio-de-janeiro_pub.zip"
        
        col1, col2 = st.columns(2)
        with col1:
            endereco_gtfs = st.text_input(
                "GTFS Entrada (endereco_gtfs)",
                value=default_gtfs,
                key="t8_endereco_gtfs_1"
            )
        with col2:
            base_resultados = st.text_input(
                "Pasta Base Resultados (BASE_RESULTADOS)",
                value=f"{base_dados.replace('dados', 'resultados')}",
                key="t8_base_resultados_1"
            )
            
        if st.button("▶ Executar Script 8", key="btn_script_8"):
            config = {
                "BASE_DADOS": st.session_state.BASE_DADOS,
                "BASE_RESULTADOS": base_resultados,
                "ano_gtfs": st.session_state.ano_gtfs,
                "mes_gtfs": st.session_state.mes_gtfs,
                "estudo_gtfs": st.session_state.estudo_gtfs,
                "endereco_gtfs": endereco_gtfs
            }
            
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "8_gerar_extensoes.py"))
            run_script(script_path, config)
            
    else:
        st.info("Utiliza sufixo no formato rio_YYYY-MM")
        default_sufixo = f"rio_{ano}-05"
        
        col1, col2 = st.columns(2)
        with col1:
            sufixo = st.text_input(
                "Sufixo (sufixo)",
                value=default_sufixo,
                key="t8_sufixo_2"
            )
            endereco_gtfs = st.text_input(
                "GTFS Entrada",
                value=f"{base_dados}/gtfs/{ano}/{default_sufixo}.zip",
                key="t8_endereco_gtfs_2"
            )
        with col2:
            base_resultados = st.text_input(
                "Pasta Base Resultados (BASE_RESULTADOS)",
                value=f"{base_dados.replace('dados', 'resultados')}",
                key="t8_base_resultados_2"
            )
            
        if st.button("▶ Executar Script 8.1", key="btn_script_81"):
            config = {
                "BASE_DADOS": st.session_state.BASE_DADOS,
                "BASE_RESULTADOS": base_resultados,
                "ano_gtfs": st.session_state.ano_gtfs,
                "sufixo": sufixo,
                "endereco_gtfs": endereco_gtfs
            }
            
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "8.1_gerar_extensoes_rio.py"))
            run_script(script_path, config)
