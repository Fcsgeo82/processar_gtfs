import streamlit as st
import os

# Configuração da página
st.set_page_config(
    page_title="Pipeline GTFS - SMTR",
    page_icon="🚌",
    layout="wide"
)

st.title("🚌 Pipeline de Processamento GTFS")
st.markdown("Aplicação para execução do pipeline de processamento e validação de GTFS da SMTR.")

# Sidebar com parâmetros globais
st.sidebar.header("⚙️ Parâmetros Globais")

# Usando session_state para compartilhar com as abas
if 'BASE_DADOS' not in st.session_state:
    st.session_state.BASE_DADOS = "C:/R_SMTR/dados"
if 'ano_gtfs' not in st.session_state:
    st.session_state.ano_gtfs = "2026"
if 'mes_gtfs' not in st.session_state:
    st.session_state.mes_gtfs = "08"
if 'estudo_gtfs' not in st.session_state:
    st.session_state.estudo_gtfs = "02"
if 'gtfs_processar' not in st.session_state:
    st.session_state.gtfs_processar = "sppo"

# Inputs na sidebar
st.session_state.BASE_DADOS = st.sidebar.text_input(
    "BASE_DADOS", 
    value=st.session_state.BASE_DADOS,
    help="Caminho base para leitura dos dados (ex: C:/R_SMTR/dados)"
)
st.session_state.ano_gtfs = st.sidebar.text_input(
    "ano_gtfs", 
    value=st.session_state.ano_gtfs,
    help="Ano de referência do GTFS (ex: 2026)"
)
st.session_state.mes_gtfs = st.sidebar.text_input(
    "mes_gtfs", 
    value=st.session_state.mes_gtfs,
    help="Mês de referência (ex: 08)"
)
st.session_state.estudo_gtfs = st.sidebar.text_input(
    "estudo_gtfs", 
    value=st.session_state.estudo_gtfs,
    help="Estudo/Quinzena (ex: 02)"
)
st.session_state.gtfs_processar = st.sidebar.selectbox(
    "gtfs_processar", 
    ["sppo", "brt", "rio"], 
    index=["sppo", "brt", "rio"].index(st.session_state.gtfs_processar),
    help="Tipo de serviço do GTFS a processar"
)

# Criação das abas
tabs = st.tabs([
    "0. Validar", 
    "1. Extrair QH", 
    "2. Ajustar ST", 
    "4. Alternativos", 
    "5. Juntar GTFS", 
    "6. Shapes", 
    "7. Partidas", 
    "8. Extensões", 
    "9. Filtrar", 
    "10. Juntar Dois"
])

# Importação preguiçosa (lazy loading) das abas para evitar recarregar tudo
from src.tabs import tab_0_validar
from src.tabs import tab_1_extrair_qh
from src.tabs import tab_2_ajustar_st
from src.tabs import tab_4_trajetos
from src.tabs import tab_5_juntar
from src.tabs import tab_6_shapes
from src.tabs import tab_7_partidas
from src.tabs import tab_8_extensoes
from src.tabs import tab_9_filtrar
from src.tabs import tab_10_juntar_dois

with tabs[0]:
    tab_0_validar.render()
with tabs[1]:
    tab_1_extrair_qh.render()
with tabs[2]:
    tab_2_ajustar_st.render()
with tabs[3]:
    tab_4_trajetos.render()
with tabs[4]:
    tab_5_juntar.render()
with tabs[5]:
    tab_6_shapes.render()
with tabs[6]:
    tab_7_partidas.render()
with tabs[7]:
    tab_8_extensoes.render()
with tabs[8]:
    tab_9_filtrar.render()
with tabs[9]:
    tab_10_juntar_dois.render()
