"""App Streamlit para carregar CSVs de quadros horários em um GTFS existente.

Substitui as frequências do GTFS pelos novos quadros e, quando necessário,
solicita autorização para clonar moldes de viagens para novos calendários.

Execução:
    python -m streamlit run src/app_carregar_qh.py
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from src.gtfs_carregar_qh import (
    ItemPlanejado,
    QuadroHorarioCSV,
    aplicar_quadros_gtfs,
    detectar_alteracoes,
    parse_qh_csv,
    read_gtfs,
    write_gtfs,
)


@st.cache_data(show_spinner="Carregando GTFS...")
def _carregar_gtfs_bytes(conteudo: bytes) -> dict[str, pd.DataFrame]:
    buf = io.BytesIO(conteudo)
    return read_gtfs(buf)


def main():
    st.set_page_config(
        page_title="Carregar Quadros Horários no GTFS",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🚌 Carregar Quadros de Horários no GTFS")
    st.markdown(
        "Atualize frequências no GTFS a partir de arquivos CSV de quadros horários "
        "(formato gerado pelos scripts `1.3` e `1.4`). "
        "A ferramenta substitui **apenas o sentido (`headsign`) e calendário (`service_id`)** indicados em cada CSV."
    )

    # ==========================================================================
    # BARRA LATERAL: ENTRADA DE DADOS
    # ==========================================================================
    st.sidebar.header("1. GTFS Base")
    modo_gtfs = st.sidebar.radio(
        "Origem do GTFS",
        ["Upload de arquivo ZIP", "Caminho no disco"],
        key="c_qh_modo_gtfs",
    )

    gtfs_dict = None
    nome_gtfs_base = "gtfs_modificado.zip"

    if modo_gtfs == "Upload de arquivo ZIP":
        up_gtfs = st.sidebar.file_uploader(
            "Selecione o GTFS (.zip)",
            type=["zip"],
            key="c_qh_up_gtfs",
        )
        if up_gtfs is not None:
            gtfs_dict = _carregar_gtfs_bytes(up_gtfs.getvalue())
            nome_gtfs_base = up_gtfs.name
            st.sidebar.success(f"GTFS carregado ({len(gtfs_dict.get('routes', []))} rotas, {len(gtfs_dict.get('trips', []))} trips)")
    else:
        caminho_local_gtfs = st.sidebar.text_input(
            "Caminho do GTFS local (.zip)",
            value="C:/R_SMTR/dados/gtfs/2026/gtfs_combi_2026-11-04Q_completo.zip",
            key="c_qh_local_gtfs",
        )
        if caminho_local_gtfs and Path(caminho_local_gtfs).is_file():
            if st.sidebar.button("Carregar GTFS do Disco", key="btn_load_disc"):
                with st.spinner("Lendo GTFS do disco..."):
                    gtfs_dict = read_gtfs(caminho_local_gtfs)
                    st.session_state["gtfs_dict_disco"] = gtfs_dict
                    st.session_state["nome_gtfs_disco"] = Path(caminho_local_gtfs).name
            if "gtfs_dict_disco" in st.session_state:
                gtfs_dict = st.session_state["gtfs_dict_disco"]
                nome_gtfs_base = st.session_state.get("nome_gtfs_disco", "gtfs_combi.zip")
                st.sidebar.success(f"GTFS carregado ({len(gtfs_dict.get('routes', []))} rotas, {len(gtfs_dict.get('trips', []))} trips)")
        else:
            st.sidebar.info("Informe um caminho válido de arquivo .zip.")

    st.sidebar.markdown("---")
    st.sidebar.header("2. Quadros de Horários (CSV)")

    service_id_fallback = st.sidebar.selectbox(
        "Calendário Padrão (se não identificado no nome)",
        ["F_REG", "U_REG", "S_REG", "D_REG", "EXCEP", "F", "U", "S", "D"],
        index=0,
        help="Usado caso o nome do arquivo CSV não termine com _F_REG, _U_REG, etc.",
        key="c_qh_sid_fallback",
    )

    modo_csvs = st.sidebar.radio(
        "Origem dos CSVs",
        ["Upload de múltiplos arquivos", "Pasta local no disco"],
        key="c_qh_modo_csvs",
    )

    quadros_lidos: List[QuadroHorarioCSV] = []

    if modo_csvs == "Upload de múltiplos arquivos":
        up_csvs = st.sidebar.file_uploader(
            "Selecione um ou mais arquivos CSV",
            type=["csv"],
            accept_multiple_files=True,
            key="c_qh_up_csvs",
        )
        if up_csvs:
            for uf in up_csvs:
                try:
                    qh = parse_qh_csv(uf, nome_arquivo=uf.name, fallback_service_id=service_id_fallback)
                    quadros_lidos.append(qh)
                except Exception as e:
                    st.sidebar.error(f"Erro em {uf.name}: {e}")
    else:
        pasta_csvs = st.sidebar.text_input(
            "Caminho da pasta com CSVs",
            value="C:/R_SMTR/resultados/quadro_horario_extraido/2026/11/qh_por_linha_partidas/05Q",
            key="c_qh_pasta_csvs",
        )
        if pasta_csvs and Path(pasta_csvs).is_dir():
            arquivos_na_pasta = sorted(Path(pasta_csvs).glob("*.csv"))
            st.sidebar.write(f"Encontrados **{len(arquivos_na_pasta)}** arquivo(s) CSV na pasta.")
            for p in arquivos_na_pasta:
                try:
                    qh = parse_qh_csv(p, fallback_service_id=service_id_fallback)
                    quadros_lidos.append(qh)
                except Exception as e:
                    st.sidebar.error(f"Erro em {p.name}: {e}")

    # ==========================================================================
    # CORPO PRINCIPAL
    # ==========================================================================
    if gtfs_dict is None:
        st.info("👈 Por favor, selecione e carregue o arquivo GTFS base na barra lateral.")
        return

    if not quadros_lidos:
        st.info("👈 Selecione ou envie os arquivos CSV dos quadros horários na barra lateral.")
        return

    st.subheader(f"📋 Análise dos Quadros Carregados ({len(quadros_lidos)} quadro(s))")

    # Detectar o plano de alterações contra o GTFS
    itens_planejados = detectar_alteracoes(gtfs_dict, quadros_lidos)

    tabela_resumo = []
    for it in itens_planejados:
        qh = it.quadro
        tabela_resumo.append({
            "Arquivo": qh.nome_origem,
            "Linha": qh.servico,
            "Headsign": qh.headsign,
            "Calendário": qh.service_id,
            "Bandas": qh.total_bandas,
            "Partidas Previstas": qh.total_partidas,
            "Status no GTFS": it.status,
            "Ação / Detalhes": it.mensagem,
        })

    df_resumo = pd.DataFrame(tabela_resumo)
    st.dataframe(df_resumo, width="stretch", hide_index=True)

    # Identificar itens que necessitam de clonagem
    itens_clonagem = [it for it in itens_planejados if it.status == "REQUER_CLONAGEM"]
    itens_diretos = [it for it in itens_planejados if it.status == "SUBSTITUICAO_DIRETA"]
    itens_erro = [it for it in itens_planejados if it.status in ("LINHA_NAO_ENCONTRADA", "ITINERARIO_NAO_ENCONTRADO")]

    c1, c2, c3 = st.columns(3)
    c1.metric("Substituições Diretas", len(itens_diretos))
    c2.metric("Requerem Clonagem de Molde", len(itens_clonagem))
    c3.metric("Não Encontrados / Ignorados", len(itens_erro))

    autorizacao_clonagem = False
    if itens_clonagem:
        st.warning(
            f"⚠️ **Atenção:** Foram identificados **{len(itens_clonagem)}** quadro(s) cujo calendário ainda não possui viagem "
            "cadastrada no GTFS. Para incluí-los, o sistema clonará a sequência de paradas e o trajeto da viagem molde de dias úteis (`U_REG`)."
        )
        autorizacao_clonagem = st.checkbox(
            "✅ **Autorizo a clonagem de viagens molde para os quadros acima listados.**",
            value=False,
            key="chk_autorizacao_clonagem",
        )

    st.markdown("---")

    # Botão de Execução
    pode_executar = True
    if itens_clonagem and not autorizacao_clonagem:
        pode_executar = False

    if st.button("🚀 Aplicar Quadros e Gerar Novo GTFS", type="primary", disabled=not pode_executar, key="btn_executar"):
        with st.spinner("Atualizando frequências e aplicando regras de integridade..."):
            try:
                logs_processo: List[str] = []
                novo_gtfs, relatorio = aplicar_quadros_gtfs(
                    gtfs_dict,
                    itens_planejados,
                    permitir_clonagem=autorizacao_clonagem,
                    logger=logs_processo.append,
                )

                st.success("✅ **Quadros horários aplicados com sucesso no GTFS!**")

                with st.expander("Ver log detalhado das alterações", expanded=False):
                    for l in logs_processo:
                        st.text(l)

                # Preparar arquivo para download
                buf_zip = io.BytesIO()
                write_gtfs(novo_gtfs, buf_zip)
                buf_zip.seek(0)

                nome_saida = f"{Path(nome_gtfs_base).stem}_atualizado_qh.zip"

                st.download_button(
                    label=f"💾 Baixar GTFS Atualizado ({nome_saida})",
                    data=buf_zip.getvalue(),
                    file_name=nome_saida,
                    mime="application/zip",
                    key="btn_download_gtfs",
                )

            except Exception as e:
                st.error(f"Erro ao processar GTFS: {e}")

    elif itens_clonagem and not autorizacao_clonagem:
        st.info("ℹ️ Para prosseguir, marque a caixa de autorização de clonagem acima.")


if __name__ == "__main__":
    main()
