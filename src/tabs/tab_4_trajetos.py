import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("4. Trajetos Alternativos")
    st.markdown("Extrai viagens com trajetos excepcionais/alternativos (definidos por calendários específicos) e gera o arquivo de OS.")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    mes = st.session_state.mes_gtfs
    estudo = st.session_state.estudo_gtfs
    
    default_gtfs = f"{base_dados}/gtfs/{ano}/sppo_{ano}-{mes}-{estudo}Q_PROC.zip"
    default_saida = f"{base_dados}/os/os_{ano}-{mes}-{estudo}_excep.csv"
    
    col1, col2 = st.columns(2)
    with col1:
        endereco_gtfs = st.text_input(
            "Caminho do GTFS (endereco_gtfs)",
            value=default_gtfs,
            help="Normalmente é o _PROC.zip gerado na etapa de ajuste",
            key="t4_endereco_gtfs"
        )
        caminho_saida = st.text_input(
            "Caminho da Saída (caminho_saida)",
            value=default_saida,
            help="Onde será salvo o arquivo de OS (CSV)",
            key="t4_caminho_saida"
        )
        
    with col2:
        calendarios = st.multiselect(
            "Calendários Alvo (CALENDARIOS_ALVO)",
            ["U", "S", "D", "EXCEP"],
            default=["EXCEP"],
            help="Apenas trips destes calendários serão extraídas",
            key="t4_calendarios"
        )
        
    if st.button("▶ Executar Script 4", key="btn_script_4"):
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "ano_gtfs": st.session_state.ano_gtfs,
            "mes_gtfs": st.session_state.mes_gtfs,
            "estudo_gtfs": st.session_state.estudo_gtfs,
            "endereco_gtfs": endereco_gtfs,
            "caminho_saida": caminho_saida,
            "CALENDARIOS_ALVO": calendarios
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "4_trajetos_alternativos.py"))
        run_script(script_path, config)
