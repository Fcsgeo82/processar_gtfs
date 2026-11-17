"""Módulo para carregar quadros de horários (CSVs) em um GTFS existente.

Realiza a operação inversa dos scripts 1 e 1.4:
Lê arquivos CSV de quadros horários (formato dos scripts 1.3 e 1.4) e
substitui as bandas de frequência correspondentes no GTFS (frequencies.txt).

Se a linha e sentido ainda não possuírem viagens para o calendário informado,
permite clonar o molde de paradas/itinerário a partir de outro calendário
(ex.: U_REG), mediante autorização do usuário.
"""

from __future__ import annotations

import io
import math
import os
import re
import unicodedata
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd


# ==============================================================================
# CONSTANTES E UTILITÁRIOS
# ==============================================================================
SERVICE_IDS_CONHECIDOS = {"U_REG", "S_REG", "D_REG", "F_REG", "U", "S", "D", "F", "EXCEP", "DESAT"}


def normalizar_texto(texto: Any) -> str:
    """Remove acentos, pontuações e converte para minúsculas para comparação flexível."""
    if pd.isna(texto) or texto is None:
        return ""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.strip().lower())


def normalizar_coluna(nome: str) -> str:
    """Normaliza nome de coluna para minúsculas sem acentos com underline."""
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", "_", s.strip().lower())


def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos."""
    if not name:
        return "SEM_NOME"
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", str(name))
    sanitized = re.sub(r"\s+", " ", sanitized).strip(". ")
    return sanitized if sanitized else "SEM_NOME"


def seconds_to_horario(total_seconds: int) -> str:
    """Converte segundos para string HH:MM:SS mantendo H >= 24."""
    if total_seconds < 0:
        return ""
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def horario_to_seconds(hk_str: Any) -> int:
    """Converte HH:MM:SS ou HH:MM para total de segundos."""
    if pd.isna(hk_str) or not str(hk_str).strip():
        return -1
    parts = str(hk_str).strip().split(":")
    if len(parts) < 2:
        return -1
    try:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) >= 3 else 0
        return h * 3600 + m * 60 + s
    except (ValueError, TypeError):
        return -1


def extrair_service_id_do_nome(nome_arquivo: str) -> Optional[str]:
    """Extrai service_id do nome do arquivo padrão horarios_{servico}_{headsign}_{service_id}.csv.

    Examina sufixos conhecidos (ex: F_REG, U_REG, S_REG, D_REG, F, U, S, D).
    """
    stem = Path(nome_arquivo).stem
    partes = stem.split("_")
    if len(partes) >= 2:
        # Testa os últimos 2 tokens (ex.: F_REG) ou último (ex.: F)
        if len(partes) >= 3:
            cand2 = f"{partes[-2]}_{partes[-1]}".upper()
            if cand2 in SERVICE_IDS_CONHECIDOS:
                return cand2
        cand1 = partes[-1].upper()
        if cand1 in SERVICE_IDS_CONHECIDOS:
            return cand1

    # Busca por regex no final do stem
    m = re.search(r"[_\-]([A-Za-z0-9]+(?:_[A-Za-z0-9]+)?)$", stem)
    if m:
        token = m.group(1).upper()
        if token in SERVICE_IDS_CONHECIDOS:
            return token
    return None


# ==============================================================================
# ESTRUTURA DE DADOS DE UM QUADRO HORÁRIO
# ==============================================================================
@dataclass
class BandaHoraria:
    start_time: str
    end_time: str
    headway_secs: int

    @property
    def start_sec(self) -> int:
        return horario_to_seconds(self.start_time)

    @property
    def end_sec(self) -> int:
        return horario_to_seconds(self.end_time)

    @property
    def n_partidas(self) -> int:
        if self.headway_secs < 1 or self.end_sec <= self.start_sec:
            return 0
        return math.ceil((self.end_sec - self.start_sec) / self.headway_secs)


@dataclass
class QuadroHorarioCSV:
    nome_origem: str
    servico: str
    headsign: str
    service_id: str
    bandas: List[BandaHoraria] = field(default_factory=list)

    @property
    def total_partidas(self) -> int:
        return sum(b.n_partidas for b in self.bandas)

    @property
    def total_bandas(self) -> int:
        return len(self.bandas)


# ==============================================================================
# LEITURA E PARSING DE CSV DE QUADRO DE HORÁRIO
# ==============================================================================
def parse_qh_csv(
    origem: Union[str, Path, BinaryIO, io.BytesIO, io.StringIO],
    nome_arquivo: str = "",
    fallback_service_id: Optional[str] = None,
) -> QuadroHorarioCSV:
    """Lê um arquivo CSV de quadro de horários e extrai suas bandas e metadados.

    Aceita caminhos de arquivo, buffers de bytes (Streamlit UploadedFile) ou strings.
    """
    if isinstance(origem, (str, Path)):
        caminho = Path(origem)
        if not nome_arquivo:
            nome_arquivo = caminho.name
        try:
            df = pd.read_csv(caminho, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(caminho, dtype=str, encoding="latin-1")
    else:
        # Buffer de bytes ou StringIO
        if hasattr(origem, "name") and not nome_arquivo:
            nome_arquivo = getattr(origem, "name")
        try:
            df = pd.read_csv(origem, dtype=str, encoding="utf-8-sig")
        except UnicodeDecodeError:
            if hasattr(origem, "seek"):
                origem.seek(0)
            df = pd.read_csv(origem, dtype=str, encoding="latin-1")

    if df.empty:
        raise ValueError(f"O arquivo {nome_arquivo or 'CSV'} está vazio.")

    # Normalizar nomes de colunas
    col_map = {c: normalizar_coluna(c) for c in df.columns}
    df = df.rename(columns=col_map)

    # Identificar colunas essenciais
    # Serviço: trip_short_name, servico, linha, route_short_name
    col_servico = next((c for c in ["trip_short_name", "servico", "linha", "route_short_name"] if c in df.columns), None)
    # Headsign: trip_headsign, headsign, vista, destino
    col_headsign = next((c for c in ["trip_headsign", "headsign", "vista", "destino"] if c in df.columns), None)
    # Horários
    col_start = next((c for c in ["start_time", "inicio", "hora_inicio"] if c in df.columns), None)
    col_end = next((c for c in ["end_time", "fim", "hora_fim"] if c in df.columns), None)
    col_headway = next((c for c in ["headway_secs", "intervalo", "headway"] if c in df.columns), None)

    obrigatorias = [("serviço", col_servico), ("headsign", col_headsign), ("start_time", col_start), ("end_time", col_end), ("headway_secs", col_headway)]
    faltantes = [rotulo for rotulo, col in obrigatorias if col is None]
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes em '{nome_arquivo}': {faltantes}. Colunas lidas: {list(df.columns)}")

    # Extrair serviço e headsign (deve ser consistente no arquivo)
    servicos_unicos = df[col_servico].dropna().str.strip().unique()
    if len(servicos_unicos) == 0:
        raise ValueError(f"Coluna de serviço vazia em '{nome_arquivo}'.")
    servico = servicos_unicos[0]

    headsigns_unicos = df[col_headsign].dropna().str.strip().unique()
    if len(headsigns_unicos) == 0:
        raise ValueError(f"Coluna de headsign vazia em '{nome_arquivo}'.")
    headsign = headsigns_unicos[0]

    # Extrair service_id do nome do arquivo ou fallback
    sid_detectado = extrair_service_id_do_nome(nome_arquivo) if nome_arquivo else None
    service_id = sid_detectado or fallback_service_id or "F_REG"

    # Construir bandas válidas
    bandas: List[BandaHoraria] = []
    for _, row in df.iterrows():
        st = str(row[col_start]).strip()
        et = str(row[col_end]).strip()
        hw_raw = str(row[col_headway]).strip().replace(",", ".")
        try:
            hw = int(round(float(hw_raw)))
        except (ValueError, TypeError):
            continue

        if st and et and hw > 0:
            bandas.append(BandaHoraria(start_time=st, end_time=et, headway_secs=hw))

    if not bandas:
        raise ValueError(f"Nenhuma banda horária válida encontrada em '{nome_arquivo}'.")

    # Ordena bandas por horário de início
    bandas.sort(key=lambda b: b.start_sec)

    return QuadroHorarioCSV(
        nome_origem=nome_arquivo or f"horarios_{servico}_{headsign}_{service_id}.csv",
        servico=servico,
        headsign=headsign,
        service_id=service_id,
        bandas=bandas,
    )


# ==============================================================================
# LEITURA E ESCRITA DO GTFS (.ZIP)
# ==============================================================================
def read_gtfs(zip_source: Union[str, Path, BinaryIO, io.BytesIO]) -> Dict[str, pd.DataFrame]:
    """Lê todas as tabelas .txt de um arquivo GTFS ZIP em um dicionário de DataFrames."""
    gtfs_data: Dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(zip_source, "r") as z:
        for fname in z.namelist():
            if fname.endswith(".txt"):
                tname = Path(fname).stem
                with z.open(fname) as f:
                    try:
                        gtfs_data[tname] = pd.read_csv(f, dtype=str)
                    except pd.errors.EmptyDataError:
                        gtfs_data[tname] = pd.DataFrame()
    return gtfs_data


def write_gtfs(gtfs_dict: Dict[str, pd.DataFrame], zip_dest: Union[str, Path, BinaryIO, io.BytesIO]) -> None:
    """Grava as tabelas do GTFS em um arquivo ZIP (caminho em disco ou buffer em memória)."""
    with zipfile.ZipFile(zip_dest, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for key, df in gtfs_dict.items():
            if df is not None and not df.empty:
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                zout.writestr(f"{key}.txt", csv_bytes)


def clean_gtfs(gtfs_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Limpeza em cascata no GTFS: remove registros órfãos com base nas trips existentes."""
    if "trips" not in gtfs_dict or gtfs_dict["trips"].empty:
        return gtfs_dict

    valid_trips = set(gtfs_dict["trips"]["trip_id"].dropna())

    if "stop_times" in gtfs_dict and not gtfs_dict["stop_times"].empty:
        gtfs_dict["stop_times"] = gtfs_dict["stop_times"][
            gtfs_dict["stop_times"]["trip_id"].isin(valid_trips)
        ]

    if "frequencies" in gtfs_dict and not gtfs_dict["frequencies"].empty:
        gtfs_dict["frequencies"] = gtfs_dict["frequencies"][
            gtfs_dict["frequencies"]["trip_id"].isin(valid_trips)
        ]

    valid_routes = set(gtfs_dict["trips"]["route_id"].dropna())
    if "routes" in gtfs_dict and not gtfs_dict["routes"].empty:
        gtfs_dict["routes"] = gtfs_dict["routes"][
            gtfs_dict["routes"]["route_id"].isin(valid_routes)
        ]

    if "shapes" in gtfs_dict and not gtfs_dict["shapes"].empty and "shape_id" in gtfs_dict["trips"].columns:
        valid_shapes = set(gtfs_dict["trips"]["shape_id"].dropna())
        gtfs_dict["shapes"] = gtfs_dict["shapes"][
            gtfs_dict["shapes"]["shape_id"].isin(valid_shapes)
        ]

    if "stop_times" in gtfs_dict and not gtfs_dict["stop_times"].empty:
        valid_stops = set(gtfs_dict["stop_times"]["stop_id"].dropna())
        if "stops" in gtfs_dict and not gtfs_dict["stops"].empty:
            df_stops = gtfs_dict["stops"]
            child_stops = df_stops[df_stops["stop_id"].isin(valid_stops)]
            if "parent_station" in child_stops.columns:
                parents = set(child_stops["parent_station"].replace("", np.nan).dropna())
                valid_stops.update(parents)
            gtfs_dict["stops"] = df_stops[df_stops["stop_id"].isin(valid_stops)]

    valid_services = set(gtfs_dict["trips"]["service_id"].dropna())
    if "calendar" in gtfs_dict and not gtfs_dict["calendar"].empty:
        gtfs_dict["calendar"] = gtfs_dict["calendar"][
            gtfs_dict["calendar"]["service_id"].isin(valid_services)
        ]
    if "calendar_dates" in gtfs_dict and not gtfs_dict["calendar_dates"].empty:
        gtfs_dict["calendar_dates"] = gtfs_dict["calendar_dates"][
            gtfs_dict["calendar_dates"]["service_id"].isin(valid_services)
        ]

    if "routes" in gtfs_dict and not gtfs_dict["routes"].empty:
        valid_agencies = (
            set(gtfs_dict["routes"]["agency_id"].dropna())
            if "agency_id" in gtfs_dict["routes"].columns
            else set()
        )
        if valid_agencies and "agency" in gtfs_dict and not gtfs_dict["agency"].empty and "agency_id" in gtfs_dict["agency"].columns:
            gtfs_dict["agency"] = gtfs_dict["agency"][
                gtfs_dict["agency"]["agency_id"].isin(valid_agencies)
            ]

    return gtfs_dict


# ==============================================================================
# DETECÇÃO E MATCHING ENTRE CSVs DE QUADROS E GTFS
# ==============================================================================
@dataclass
class ItemPlanejado:
    quadro: QuadroHorarioCSV
    status: str  # 'SUBSTITUICAO_DIRETA', 'REQUER_CLONAGEM', 'LINHA_NAO_ENCONTRADA', 'ITINERARIO_NAO_ENCONTRADO'
    route_id: Optional[str] = None
    target_trip_id: Optional[str] = None
    existing_trip_ids: List[str] = field(default_factory=list)
    molde_trip_id: Optional[str] = None
    molde_service_id: Optional[str] = None
    mensagem: str = ""


def encontrar_route_id(df_routes: pd.DataFrame, servico: str) -> Optional[str]:
    """Busca o route_id de um serviço (route_short_name), ignorando maiúsculas e espaços."""
    if df_routes.empty or "route_short_name" not in df_routes.columns:
        return None
    s_norm = normalizar_texto(servico)
    # Match exato primeiro
    m = df_routes[df_routes["route_short_name"].astype(str).str.strip().str.upper() == servico.upper()]
    if not m.empty:
        return m.iloc[0]["route_id"]

    # Match normalizado
    for _, r in df_routes.iterrows():
        if normalizar_texto(r.get("route_short_name", "")) == s_norm:
            return r["route_id"]
    return None


def match_headsign(headsign_procurado: str, df_trips_candidatas: pd.DataFrame) -> pd.DataFrame:
    """Filtra trips candidatas que correspondem ao headsign procurado.

    Tenta:
    1. Match exato
    2. Match normalizado (sem acentos/espaços)
    3. Match por destino (ex.: se headsign for 'A - B', testa 'B')
    """
    if df_trips_candidatas.empty or "trip_headsign" not in df_trips_candidatas.columns:
        return pd.DataFrame()

    hs_norm = normalizar_texto(headsign_procurado)

    # 1. Match exato
    m = df_trips_candidatas[df_trips_candidatas["trip_headsign"].astype(str).str.strip() == headsign_procurado.strip()]
    if not m.empty:
        return m

    # 2. Match normalizado
    mask_norm = df_trips_candidatas["trip_headsign"].apply(normalizar_texto) == hs_norm
    m = df_trips_candidatas[mask_norm]
    if not m.empty:
        return m

    # 3. Match se headsign procurado é destino de uma vista 'Origem - Destino'
    partes = str(headsign_procurado).split(" - ")
    if len(partes) == 2:
        destino_norm = normalizar_texto(partes[1])
        mask_dest = df_trips_candidatas["trip_headsign"].apply(normalizar_texto) == destino_norm
        m = df_trips_candidatas[mask_dest]
        if not m.empty:
            return m

    return pd.DataFrame()


def detectar_alteracoes(gtfs_dict: Dict[str, pd.DataFrame], lista_qh: List[QuadroHorarioCSV]) -> List[ItemPlanejado]:
    """Analisa os quadros fornecidos contra o GTFS e planeja as ações necessárias."""
    df_routes = gtfs_dict.get("routes", pd.DataFrame())
    df_trips = gtfs_dict.get("trips", pd.DataFrame())

    itens: List[ItemPlanejado] = []

    for qh in lista_qh:
        route_id = encontrar_route_id(df_routes, qh.servico)
        if not route_id:
            itens.append(
                ItemPlanejado(
                    quadro=qh,
                    status="LINHA_NAO_ENCONTRADA",
                    mensagem=f"Linha '{qh.servico}' não encontrada em routes.txt do GTFS.",
                )
            )
            continue

        # Trips regulares da rota (exclui EXCEP e desvios com '[')
        trips_rota = df_trips[df_trips["route_id"] == route_id].copy()
        if "trip_headsign" in trips_rota.columns:
            mask_regular = ~trips_rota["trip_headsign"].astype(str).str.contains(r"\[", regex=True)
            if mask_regular.any():
                trips_rota = trips_rota[mask_regular]

        # 1. Verifica se já existem trips para o service_id pretendido
        trips_mesmo_servico = trips_rota[trips_rota["service_id"] == qh.service_id]
        matching_trips = match_headsign(qh.headsign, trips_mesmo_servico)

        if not matching_trips.empty:
            existing_tids = matching_trips["trip_id"].tolist()
            target_tid = existing_tids[0]
            itens.append(
                ItemPlanejado(
                    quadro=qh,
                    status="SUBSTITUICAO_DIRETA",
                    route_id=route_id,
                    target_trip_id=target_tid,
                    existing_trip_ids=existing_tids,
                    mensagem=f"Substituição direta: {len(existing_tids)} trip(s) existente(s) identificada(s).",
                )
            )
        else:
            # 2. Precisa de molde de outro calendário
            # Ordem de preferência de serviço base: U_REG, U, S_REG, S, D_REG, D, outros
            ordem_base = ["U_REG", "U", "S_REG", "S", "D_REG", "D"]
            servicos_disponiveis = [s for s in ordem_base if s in trips_rota["service_id"].values]
            outros_s = [s for s in trips_rota["service_id"].unique() if s not in ordem_base and s != qh.service_id]
            todos_candidatos = servicos_disponiveis + outros_s

            molde_encontrado: Optional[Tuple[str, str]] = None
            for sid_candidato in todos_candidatos:
                trips_cand = trips_rota[trips_rota["service_id"] == sid_candidato]
                m_molde = match_headsign(qh.headsign, trips_cand)
                if not m_molde.empty:
                    molde_encontrado = (m_molde.iloc[0]["trip_id"], sid_candidato)
                    break

            if molde_encontrado:
                molde_tid, molde_sid = molde_encontrado
                itens.append(
                    ItemPlanejado(
                        quadro=qh,
                        status="REQUER_CLONAGEM",
                        route_id=route_id,
                        molde_trip_id=molde_tid,
                        molde_service_id=molde_sid,
                        mensagem=f"Não há viagem para {qh.service_id}. Requer clonar molde de {molde_sid} (trip: {molde_tid}).",
                    )
                )
            else:
                itens.append(
                    ItemPlanejado(
                        quadro=qh,
                        status="ITINERARIO_NAO_ENCONTRADO",
                        route_id=route_id,
                        mensagem=f"Itinerário com headsign '{qh.headsign}' não encontrado em nenhum calendário da linha {qh.servico}.",
                    )
                )

    return itens


# ==============================================================================
# APLICAÇÃO DAS ALTERAÇÕES NO GTFS
# ==============================================================================
def aplicar_quadros_gtfs(
    gtfs_dict: Dict[str, pd.DataFrame],
    itens_planejados: List[ItemPlanejado],
    permitir_clonagem: bool = False,
    logger: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, pd.DataFrame], List[Dict[str, Any]]]:
    """Aplica a substituição das bandas de frequência no GTFS.

    Retorna uma cópia atualizada do GTFS e um resumo das operações executadas.
    """
    def log(msg: str):
        if logger:
            logger(msg)

    # Cria cópia profunda das tabelas afetadas
    novo_gtfs = {k: v.copy() for k, v in gtfs_dict.items()}

    df_trips = novo_gtfs.get("trips", pd.DataFrame()).copy()
    df_st = novo_gtfs.get("stop_times", pd.DataFrame()).copy()
    df_freq = novo_gtfs.get("frequencies", pd.DataFrame()).copy()
    df_cal = novo_gtfs.get("calendar", pd.DataFrame()).copy()

    # Garante estrutura mínima em frequencies.txt
    if df_freq.empty or "trip_id" not in df_freq.columns:
        df_freq = pd.DataFrame(columns=["trip_id", "start_time", "end_time", "headway_secs", "exact_times"])
    if "exact_times" not in df_freq.columns:
        df_freq["exact_times"] = "0"

    relatorio_execucao: List[Dict[str, Any]] = []

    # Validar se há itens que requerem clonagem não autorizada
    itens_clonagem = [it for it in itens_planejados if it.status == "REQUER_CLONAGEM"]
    if itens_clonagem and not permitir_clonagem:
        linhas_pendentes = [f"{it.quadro.servico} ({it.quadro.headsign})" for it in itens_clonagem]
        raise PermissionError(
            f"Clonagem de viagens não autorizada pelo usuário. As seguintes linhas requerem clonagem: {', '.join(linhas_pendentes)}."
        )

    for item in itens_planejados:
        qh = item.quadro

        if item.status in ("LINHA_NAO_ENCONTRADA", "ITINERARIO_NAO_ENCONTRADO"):
            log(f"⚠️ Ignorado: {qh.servico} ({qh.headsign}) — {item.mensagem}")
            relatorio_execucao.append({
                "servico": qh.servico,
                "headsign": qh.headsign,
                "service_id": qh.service_id,
                "status": "IGNORADO",
                "detalhes": item.mensagem,
                "bandas_inseridas": 0,
                "partidas_inseridas": 0,
            })
            continue

        target_trip_id = item.target_trip_id

        # Se requer clonagem
        if item.status == "REQUER_CLONAGEM":
            molde_tid = item.molde_trip_id
            molde_trip_row = df_trips[df_trips["trip_id"] == molde_tid].iloc[0].to_dict()

            # Gera novo trip_id único e legível
            hs_clean = sanitize_filename(qh.headsign)
            novo_tid = f"TRIP_{qh.servico}_{hs_clean}_{qh.service_id}_{uuid.uuid4().hex[:6]}"

            # Nova trip
            nova_trip = molde_trip_row.copy()
            nova_trip["trip_id"] = novo_tid
            nova_trip["service_id"] = qh.service_id
            df_trips = pd.concat([df_trips, pd.DataFrame([nova_trip])], ignore_index=True)

            # Clona paradas de stop_times
            paradas_molde = df_st[df_st["trip_id"] == molde_tid].copy()
            if not paradas_molde.empty:
                paradas_molde["trip_id"] = novo_tid
                df_st = pd.concat([df_st, paradas_molde], ignore_index=True)

            # Garante que o service_id exista em calendar.txt se calendar.txt existir
            if not df_cal.empty and "service_id" in df_cal.columns:
                if qh.service_id not in df_cal["service_id"].values:
                    # Clona configuração do molde_service_id se existir, ou cria dias padrão
                    molde_cal = df_cal[df_cal["service_id"] == item.molde_service_id]
                    if not molde_cal.empty:
                        novo_cal_row = molde_cal.iloc[0].to_dict()
                        novo_cal_row["service_id"] = qh.service_id
                    else:
                        novo_cal_row = {c: "0" for c in df_cal.columns}
                        novo_cal_row["service_id"] = qh.service_id
                        novo_cal_row["start_date"] = "20240101"
                        novo_cal_row["end_date"] = "20281231"
                        if "F" in qh.service_id:
                            novo_cal_row["monday"] = "1"
                            novo_cal_row["tuesday"] = "1"
                            novo_cal_row["wednesday"] = "1"
                            novo_cal_row["thursday"] = "1"
                            novo_cal_row["friday"] = "1"
                    df_cal = pd.concat([df_cal, pd.DataFrame([novo_cal_row])], ignore_index=True)

            target_trip_id = novo_tid
            log(f"  ✓ Clonada viagem molde {molde_tid} ({item.molde_service_id}) -> {novo_tid} para {qh.service_id}")

        else:
            # Substituição direta: remove frequências antigas de TODAS as trips daquele sentido/service_id
            tids_a_limpar = item.existing_trip_ids
            df_freq = df_freq[~df_freq["trip_id"].isin(tids_a_limpar)]
            log(f"  ✓ Frequências antigas removidas para as trips: {tids_a_limpar}")

        # Inserir as novas bandas em frequencies.txt vinculadas ao target_trip_id
        novas_linhas_freq = []
        for b in qh.bandas:
            novas_linhas_freq.append({
                "trip_id": target_trip_id,
                "start_time": b.start_time,
                "end_time": b.end_time,
                "headway_secs": str(b.headway_secs),
                "exact_times": "0",
            })

        df_freq = pd.concat([df_freq, pd.DataFrame(novas_linhas_freq)], ignore_index=True)
        log(f"  ✓ {len(novas_linhas_freq)} bandas ({qh.total_partidas} partidas) inseridas para {qh.servico} - {qh.headsign} ({qh.service_id})")

        relatorio_execucao.append({
            "servico": qh.servico,
            "headsign": qh.headsign,
            "service_id": qh.service_id,
            "status": "SUCESSO",
            "tipo_operacao": "CLONAGEM" if item.status == "REQUER_CLONAGEM" else "SUBSTITUICAO_DIRETA",
            "trip_id": target_trip_id,
            "bandas_inseridas": len(novas_linhas_freq),
            "partidas_inseridas": qh.total_partidas,
        })

    novo_gtfs["trips"] = df_trips
    novo_gtfs["stop_times"] = df_st
    novo_gtfs["frequencies"] = df_freq
    if not df_cal.empty:
        novo_gtfs["calendar"] = df_cal

    # Limpeza em cascata final
    novo_gtfs = clean_gtfs(novo_gtfs)

    return novo_gtfs, relatorio_execucao
