import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("2. Ajustar Stop Times")
    st.markdown("Ajusta as distâncias (`shape_dist_traveled`) e recalcula os horários (`arrival_time`, `departure_time`) de um GTFS específico baseado numa velocidade padrão.")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    mes = st.session_state.mes_gtfs
    estudo = st.session_state.estudo_gtfs
    processar = st.session_state.gtfs_processar
    
    default_gtfs = f"{base_dados}/gtfs/{ano}/{processar}_{ano}-{mes}-{estudo}Q.zip"
    
    col1, col2 = st.columns(2)
    with col1:
        endereco_gtfs = st.text_input(
            "Caminho do GTFS Original (endereco_gtfs)",
            value=default_gtfs,
            help="O script gerará um sufixo _PROC.zip",
            key="t2_endereco_gtfs"
        )
        velocidade = st.number_input(
            "Velocidade Padrão km/h",
            value=15.0,
            step=1.0,
            help="Velocidade utilizada para recalcular os stop times a partir da distância",
            key="t2_velocidade"
        )
    with col2:
        ano_vel = st.text_input(
            "Ano (Dados Velocidade GPS)",
            value="2025",
            help="Referência para os dados GPS no relatório",
            key="t2_ano_vel"
        )
        mes_vel = st.text_input(
            "Mês (Dados Velocidade GPS)",
            value="10",
            help="Referência para os dados GPS no relatório",
            key="t2_mes_vel"
        )
        
    if st.button("▶ Executar Script 2", key="btn_script_2"):
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "ano_velocidade": ano_vel,
            "mes_velocidade": mes_vel,
            "ano_gtfs": st.session_state.ano_gtfs,
            "mes_gtfs": st.session_state.mes_gtfs,
            "estudo_gtfs": st.session_state.estudo_gtfs,
            "gtfs_processar": st.session_state.gtfs_processar,
            "endereco_gtfs": endereco_gtfs,
            "velocidade_padrao_kmh": velocidade
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "2_ajustar_stop_times.py"))
        run_script(script_path, config)
