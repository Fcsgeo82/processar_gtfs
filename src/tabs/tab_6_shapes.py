import streamlit as st
from pathlib import Path
import os
from src.runner import run_script

def render():
    st.header("6. Gerar Shapes")
    st.markdown("Transforma os dados de `shapes.txt` em um arquivo geoespacial (shapefile ou geojson) com as linhas e rotas do GTFS.")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    mes = st.session_state.mes_gtfs
    estudo = st.session_state.estudo_gtfs
    
    default_gtfs = f"{base_dados}/gtfs/{ano}/gtfs_rio-de-janeiro_pub.zip"
    default_saida = f"{base_dados}/shapes/{ano}"
    
    col1, col2 = st.columns(2)
    with col1:
        endereco_gtfs_combi = st.text_input(
            "GTFS de Entrada (endereco_gtfs_combi)",
            value=default_gtfs,
            help="Geralmente o GTFS público final",
            key="t6_endereco_gtfs"
        )
    with col2:
        pasta_shape_sppo = st.text_input(
            "Pasta Saída (pasta_shape_sppo)",
            value=default_saida,
            help="Onde o shapefile final será salvo",
            key="t6_pasta_saida"
        )
        
    if st.button("▶ Executar Script 6", key="btn_script_6"):
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "ano_gtfs": st.session_state.ano_gtfs,
            "mes_gtfs": st.session_state.mes_gtfs,
            "estudo_gtfs": st.session_state.estudo_gtfs,
            "endereco_gtfs_combi": endereco_gtfs_combi,
            "pasta_shape_sppo": pasta_shape_sppo
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "6_gerar_shapes.py"))
        run_script(script_path, config)
