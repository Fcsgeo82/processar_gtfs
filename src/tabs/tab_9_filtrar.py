import streamlit as st
from pathlib import Path
import os
import pandas as pd
from src.runner import run_script

def render():
    st.header("9. Filtrar GTFS por Lista")
    st.markdown("Filtra um GTFS removendo ou isolando viagens baseado numa tabela (TSV/CSV) de trajetos excepcionais.")
    
    st.subheader("Parâmetros Específicos")
    
    base_dados = st.session_state.BASE_DADOS
    ano = st.session_state.ano_gtfs
    
    default_sufixo = f"{ano}-12-08Q"
    
    col1, col2 = st.columns(2)
    with col1:
        ano_gtfs = st.text_input("Ano (ano_gtfs)", value=ano, key="t9_ano_gtfs")
        mes_gtfs = st.text_input("Mês (mes_gtfs)", value="12", key="t9_mes_gtfs")
        estudo_gtfs = st.text_input("Estudo (estudo_gtfs)", value="08", key="t9_estudo_gtfs")
        
        endereco_gtfs = st.text_input(
            "GTFS de Entrada (endereco_gtfs)",
            value=f"{base_dados}/gtfs/{ano_gtfs}/sppo_{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q_PROC.zip",
            key="t9_endereco_gtfs"
        )
        caminho_saida = st.text_input(
            "GTFS de Saída (caminho_saida)",
            value=f"{base_dados}/gtfs/{ano_gtfs}/sppo_{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q_FILTRADO.zip",
            key="t9_caminho_saida"
        )
        
    with col2:
        calendarios = st.multiselect(
            "Calendários Alvo (CALENDARIOS_ALVO)",
            ["U", "S", "D", "EXCEP"],
            default=["EXCEP"],
            key="t9_calendarios"
        )
        
    st.markdown("---")
    st.subheader("Lista de Filtro")
    st.markdown("Você pode colar os dados (formato TSV) na caixa de texto OU fazer upload de um CSV/TSV.")
    
    lista_default = """Serviço\tVista\tConsórcio\tSentido\tExtensão\tEvento
104\tSão Conrado - Terminal Gentileza\tIntersul\tIda\t27.085\t[desvio_feira]
104\tSão Conrado - Terminal Gentileza\tIntersul\tVolta\t26.369\t[desvio_feira]"""
    
    uploaded_file = st.file_uploader("Upload CSV/TSV", type=["csv", "tsv", "txt"], key="t9_uploaded_file")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep="\t" if uploaded_file.name.endswith(("tsv", "txt")) else ",")
            lista_raw = df.to_csv(index=False, sep="\t")
            st.success(f"Arquivo lido com sucesso: {len(df)} linhas.")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
            lista_raw = lista_default
    else:
        lista_raw = st.text_area("Dados (TSV)", value=lista_default, height=300, key="t9_lista_raw")
        
    if st.button("▶ Executar Script 9", key="btn_script_9"):
        config = {
            "BASE_DADOS": st.session_state.BASE_DADOS,
            "ano_gtfs": ano_gtfs,
            "mes_gtfs": mes_gtfs,
            "estudo_gtfs": estudo_gtfs,
            "endereco_gtfs": endereco_gtfs,
            "caminho_saida": caminho_saida,
            "CALENDARIOS_ALVO": calendarios,
            "LISTA_FILTRO_RAW": lista_raw
        }
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "codigos_py", "9_filtrar_gtfs_por_lista.py"))
        run_script(script_path, config)
