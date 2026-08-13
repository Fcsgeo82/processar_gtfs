import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("10. Juntar Dois GTFS")
    st.markdown("Junta dois arquivos GTFS dando prioridade ao arquivo principal (filtrado) em caso de chave duplicada.")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    
    col1, col2 = st.columns(2)
    with col1:
        ano_gtfs = st.text_input("Ano (ano_gtfs) - Script 10", value=ano, key="t10_ano_gtfs")
        mes_gtfs = st.text_input("Mês (mes_gtfs) - Script 10", value="12", key="t10_mes_gtfs")
        estudo_gtfs = st.text_input("Estudo (estudo_gtfs) - Script 10", value="08", key="t10_estudo_gtfs")
        
        default_sufixo = f"{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q"
        
    with col2:
        gtfs_principal = st.text_input(
            "GTFS Principal (GTFS_PRINCIPAL)",
            value=f"{base_dados}/gtfs/{ano_gtfs}/sppo_{default_sufixo}_FILTRADO.zip",
            help="Tem PRIORIDADE em caso de chave duplicada",
            key="t10_gtfs_principal"
        )
        gtfs_secundario = st.text_input(
            "GTFS Secundário (GTFS_SECUNDARIO)",
            value=f"{base_dados}/gtfs/{ano_gtfs}/sppo_{default_sufixo}_PROC.zip",
            key="t10_gtfs_secundario"
        )
        gtfs_saida = st.text_input(
            "GTFS Saída (GTFS_SAIDA)",
            value=f"{base_dados}/gtfs/{ano_gtfs}/sppo_{default_sufixo}_COMBINADO.zip",
            key="t10_gtfs_saida"
        )
        
    if st.button("▶ Executar Script 10", key="btn_script_10"):
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "ano_gtfs": ano_gtfs,
            "mes_gtfs": mes_gtfs,
            "estudo_gtfs": estudo_gtfs,
            "GTFS_PRINCIPAL": gtfs_principal,
            "GTFS_SECUNDARIO": gtfs_secundario,
            "GTFS_SAIDA": gtfs_saida
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "10_juntar_dois_gtfs.py"))
        run_script(script_path, config)
