import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("1. Extrair QH Especificado no GTFS")
    st.markdown("Extrai quadros de horários para linhas e serviços específicos a partir do GTFS Combinado.")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    mes = st.session_state.mes_gtfs
    estudo = st.session_state.estudo_gtfs
    
    default_gtfs = f"{base_dados}/gtfs/{ano}/gtfs_combi_{ano}-{mes}-{estudo}Q.zip"
    
    col1, col2 = st.columns(2)
    with col1:
        end_gtfs = st.text_input(
            "Caminho GTFS Combinado (end_gtfs)",
            value=default_gtfs,
            help="Caminho do GTFS combi",
            key="t1_end_gtfs"
        )
        base_resultados = st.text_input(
            "Pasta de Resultados (BASE_RESULTADOS)",
            value=f"{base_dados.replace('dados', 'resultados')}",
            help="Pasta base para a saída (será subpasta quadro_horario_extraido/...)",
            key="t1_base_resultados"
        )
        
    with col2:
        linhas_str = st.text_input(
            "Linhas a Rodar (separadas por vírgula)",
            value="371, 624, SN624, SV624",
            help="Lista de 'trip_short_name' para extrair. Ex: 371, 624",
            key="t1_linhas_str"
        )
        servicos = st.multiselect(
            "Calendários Alvo (services_to_run)",
            ["U_REG", "S_REG", "D_REG", "EXCEP", "U", "S", "D"],
            default=["U_REG", "S_REG", "D_REG"],
            help="Selecione os 'service_id' a serem extraídos",
            key="t1_servicos"
        )
    
    if st.button("▶ Executar Script 1", key="btn_script_1"):
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "BASE_RESULTADOS": base_resultados,
            "ano_gtfs": st.session_state.ano_gtfs,
            "mes_gtfs": st.session_state.mes_gtfs,
            "estudo_gtfs": st.session_state.estudo_gtfs,
            "end_gtfs": end_gtfs,
            "linhas_rodar": linhas_str,
            "services_to_run": servicos
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "1_extrair_qh_especificado_no_gtfs.py"))
        run_script(script_path, config)
