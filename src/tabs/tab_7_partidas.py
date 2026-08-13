import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("7. Lista Partidas")
    st.markdown("Lista as partidas por linha baseando-se nos horários da primeira parada (stop_times).")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    
    default_gtfs = f"{base_dados}/gtfs/{ano}/gtfs_rio-de-janeiro_pub.zip"
    
    col1, col2 = st.columns(2)
    with col1:
        endereco_gtfs = st.text_input(
            "GTFS Entrada (endereco_gtfs)",
            value=default_gtfs,
            key="t7_endereco_gtfs"
        )
        base_resultados = st.text_input(
            "Pasta de Resultados (BASE_RESULTADOS)",
            value=f"{base_dados.replace('dados', 'resultados')}",
            key="t7_base_resultados"
        )
    with col2:
        tipos_dia = st.multiselect(
            "Tipos de Dia (tipos_dia)",
            ["du", "sab", "dom"],
            default=["du", "sab", "dom"],
            help="Quais dias processar",
            key="t7_tipos_dia"
        )
        linhas_excluir = st.text_area(
            "Linhas a Excluir (linhas_excluir)",
            value="",
            help="Insira os trip_short_name separados por vírgula (ou um por linha)",
            key="t7_linhas_excluir"
        )
        
    if st.button("▶ Executar Script 7", key="btn_script_7"):
        # Limpar linhas excluir
        linhas = [x.strip() for x in linhas_excluir.split(',') if x.strip()] if ',' in linhas_excluir else [x.strip() for x in linhas_excluir.split('\n') if x.strip()]
        
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "BASE_RESULTADOS": base_resultados,
            "ano_gtfs": st.session_state.ano_gtfs,
            "endereco_gtfs": endereco_gtfs,
            "tipos_dia": tipos_dia,
            "linhas_excluir": linhas
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "7_lista_partidas.py"))
        run_script(script_path, config)
