import pandas as pd
import numpy as np
import zipfile
import io
import os
import time
from pathlib import Path
import warnings
import sys

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

import argparse
import json

# ==============================================================================
# LEITURA DE CONFIGURAÇÃO (Streamlit)
# ==============================================================================
_parser = argparse.ArgumentParser()
_parser.add_argument('--config', type=str, default='', help='Caminho para arquivo JSON de configuração')
_args, _ = _parser.parse_known_args()
_config = {}
if _args.config:
    with open(_args.config, 'r', encoding='utf-8') as _f:
        _config = json.load(_f)

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
BASE_DADOS = Path(_config.get("BASE_DADOS", "C:/R_SMTR/dados"))

ano_gtfs    = _config.get("ano_gtfs", "2026")
mes_gtfs    = _config.get("mes_gtfs", "12")
estudo_gtfs = _config.get("estudo_gtfs", "17")  # ESTUDO, NÃO CONSIDERAR MAIS QUINZENA!!!!
sufixo      = f"{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q"

# GTFS de entrada: o GTFS filtrado tem PRIORIDADE em caso de chave duplicada
GTFS_PRINCIPAL  = Path(_config.get("GTFS_PRINCIPAL", BASE_DADOS / f"gtfs/{ano_gtfs}/sppo_{sufixo}_FILTRADO.zip"))
GTFS_SECUNDARIO = Path(_config.get("GTFS_SECUNDARIO", BASE_DADOS / f"gtfs/{ano_gtfs}/sppo_{sufixo}_PROC.zip"))

GTFS_SAIDA = Path(_config.get("GTFS_SAIDA", BASE_DADOS / f"gtfs/{ano_gtfs}/sppo_{sufixo}_COMBINADO.zip"))

# ==============================================================================
# CHAVES PRIMÁRIAS POR TABELA GTFS
# Usadas para resolver conflitos: em caso de mesma chave, prevalece o PRINCIPAL.
# Tabelas sem chave definida usam drop_duplicates() na linha inteira.
# ==============================================================================
CHAVES_PRIMARIAS = {
    'agency':         ['agency_id'],
    'stops':          ['stop_id'],
    'routes':         ['route_id'],
    'trips':          ['trip_id'],
    'stop_times':     ['trip_id', 'stop_sequence'],
    'calendar':       ['service_id'],
    'calendar_dates': ['service_id', 'date'],
    'shapes':         ['shape_id', 'shape_pt_sequence'],
    'frequencies':    ['trip_id', 'start_time'],
    'fare_attributes':['fare_id'],
    'fare_rules':     ['fare_id', 'route_id'],
    'feed_info':      [],   # sem chave: mantém apenas a linha do principal
}

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def log_msg(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}")


def read_gtfs(zip_path):
    log_msg(f"Lendo GTFS: {zip_path}")
    gtfs_data = {}
    with zipfile.ZipFile(zip_path, 'r') as z:
        for fname in z.namelist():
            if fname.endswith('.txt'):
                with z.open(fname) as f:
                    try:
                        gtfs_data[fname.split('.')[0]] = pd.read_csv(f, dtype=str)
                    except pd.errors.EmptyDataError:
                        gtfs_data[fname.split('.')[0]] = pd.DataFrame()
    return gtfs_data


def write_gtfs(gtfs_dict, zip_path):
    log_msg(f"Salvando GTFS em: {zip_path}")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as zout:
        for key, df in gtfs_dict.items():
            if not df.empty:
                csv_bytes = df.to_csv(index=False).encode('utf-8')
                zout.writestr(f"{key}.txt", csv_bytes)


def merge_tabela(nome: str, df_principal: pd.DataFrame, df_secundario: pd.DataFrame) -> pd.DataFrame:
    """
    Combina duas tabelas de GTFS para um mesmo arquivo (ex: trips.txt).

    Estratégia por chave primária:
      - Concatena principal + secundário.
      - Remove duplicatas exatas (linha inteira) primeiro.
      - Em seguida, remove duplicatas por chave primária, mantendo a ocorrência
        do PRINCIPAL (que vem primeiro no concat).

    Tabelas sem chave definida: remove apenas duplicatas exatas.
    Tabela feed_info: mantém somente o registro do principal, se houver.
    """
    chaves = CHAVES_PRIMARIAS.get(nome)

    if df_principal.empty and df_secundario.empty:
        return pd.DataFrame()

    if df_principal.empty:
        return df_secundario.drop_duplicates()

    if df_secundario.empty:
        return df_principal.drop_duplicates()

    # feed_info: usa apenas o principal
    if nome == 'feed_info':
        return df_principal.drop_duplicates().head(1)

    # Sem chave primária definida: drop_duplicates na linha inteira
    if chaves is None:
        df_concat = pd.concat([df_principal, df_secundario], ignore_index=True)
        return df_concat.drop_duplicates()

    # Com chave primária: principal tem precedência
    # Alinha colunas: preenche com NaN as colunas ausentes em cada lado
    todas_colunas = list(dict.fromkeys(list(df_principal.columns) + list(df_secundario.columns)))
    df_p = df_principal.reindex(columns=todas_colunas)
    df_s = df_secundario.reindex(columns=todas_colunas)

    # Concatena: principal primeiro para garantir precedência no keep='first'
    df_concat = pd.concat([df_p, df_s], ignore_index=True)

    # Remove duplicatas exatas antes de resolver por chave
    antes_exatas = len(df_concat)
    df_concat = df_concat.drop_duplicates()
    removidas_exatas = antes_exatas - len(df_concat)

    # Verifica se as chaves existem no DataFrame resultante
    chaves_validas = [c for c in chaves if c in df_concat.columns]
    if chaves_validas:
        antes_chave = len(df_concat)
        df_concat = df_concat.drop_duplicates(subset=chaves_validas, keep='first')
        removidas_chave = antes_chave - len(df_concat)
    else:
        removidas_chave = 0

    total_removidas = removidas_exatas + removidas_chave
    if total_removidas > 0:
        log_msg(
            f"  {nome}: {antes_exatas} → {len(df_concat)} linhas "
            f"({removidas_exatas} duplicatas exatas + {removidas_chave} conflitos de chave resolvidos)"
        )

    return df_concat


def clean_gtfs(gtfs_dict: dict) -> dict:
    """Filtra todas as tabelas associadas com base nas trips existentes."""
    if 'trips' not in gtfs_dict or gtfs_dict['trips'].empty:
        return gtfs_dict

    valid_trips = set(gtfs_dict['trips']['trip_id'])

    if 'stop_times' in gtfs_dict and not gtfs_dict['stop_times'].empty:
        gtfs_dict['stop_times'] = gtfs_dict['stop_times'][
            gtfs_dict['stop_times']['trip_id'].isin(valid_trips)
        ]

    if 'frequencies' in gtfs_dict and not gtfs_dict['frequencies'].empty:
        gtfs_dict['frequencies'] = gtfs_dict['frequencies'][
            gtfs_dict['frequencies']['trip_id'].isin(valid_trips)
        ]

    valid_routes = set(gtfs_dict['trips']['route_id'])
    if 'routes' in gtfs_dict and not gtfs_dict['routes'].empty:
        gtfs_dict['routes'] = gtfs_dict['routes'][
            gtfs_dict['routes']['route_id'].isin(valid_routes)
        ]

    if 'shapes' in gtfs_dict and not gtfs_dict['shapes'].empty \
            and 'shape_id' in gtfs_dict['trips'].columns:
        valid_shapes = set(gtfs_dict['trips']['shape_id'].dropna())
        gtfs_dict['shapes'] = gtfs_dict['shapes'][
            gtfs_dict['shapes']['shape_id'].isin(valid_shapes)
        ]

    if 'stop_times' in gtfs_dict and not gtfs_dict['stop_times'].empty:
        valid_stops = set(gtfs_dict['stop_times']['stop_id'])
        if 'stops' in gtfs_dict and not gtfs_dict['stops'].empty:
            df_stops = gtfs_dict['stops']
            child_stops = df_stops[df_stops['stop_id'].isin(valid_stops)]
            if 'parent_station' in child_stops.columns:
                parents = set(child_stops['parent_station'].replace("", np.nan).dropna())
                valid_stops.update(parents)
            gtfs_dict['stops'] = df_stops[df_stops['stop_id'].isin(valid_stops)]

    valid_services = set(gtfs_dict['trips']['service_id'].dropna())
    if 'calendar' in gtfs_dict and not gtfs_dict['calendar'].empty:
        gtfs_dict['calendar'] = gtfs_dict['calendar'][
            gtfs_dict['calendar']['service_id'].isin(valid_services)
        ]
    if 'calendar_dates' in gtfs_dict and not gtfs_dict['calendar_dates'].empty:
        gtfs_dict['calendar_dates'] = gtfs_dict['calendar_dates'][
            gtfs_dict['calendar_dates']['service_id'].isin(valid_services)
        ]

    if 'routes' in gtfs_dict and not gtfs_dict['routes'].empty:
        valid_agencies = (
            set(gtfs_dict['routes']['agency_id'].dropna())
            if 'agency_id' in gtfs_dict['routes'].columns else set()
        )
        if valid_agencies and 'agency' in gtfs_dict \
                and not gtfs_dict['agency'].empty \
                and 'agency_id' in gtfs_dict['agency'].columns:
            gtfs_dict['agency'] = gtfs_dict['agency'][
                gtfs_dict['agency']['agency_id'].isin(valid_agencies)
            ]

    return gtfs_dict


# ==============================================================================
# PROCESSAMENTO PRINCIPAL
# ==============================================================================
print("\n╔════════════════════════════════════════════════════════════════════════════╗")
print("║                    JUNÇÃO DE DOIS GTFS SEM DUPLICAÇÕES                    ║")
print("╚════════════════════════════════════════════════════════════════════════════╝\n")

tempo_inicio = time.time()

# 1. Verificar arquivos de entrada
for caminho in [GTFS_PRINCIPAL, GTFS_SECUNDARIO]:
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo GTFS não encontrado: {caminho}")

# 2. Carregar os dois GTFSs
gtfs_p = read_gtfs(GTFS_PRINCIPAL)
gtfs_s = read_gtfs(GTFS_SECUNDARIO)

log_msg(f"Principal  — trips: {len(gtfs_p.get('trips', pd.DataFrame()))}")
log_msg(f"Secundário — trips: {len(gtfs_s.get('trips', pd.DataFrame()))}")

# 3. Combinar tabela a tabela
log_msg("Combinando tabelas e resolvendo duplicatas...")
todas_chaves = list(dict.fromkeys(list(gtfs_p.keys()) + list(gtfs_s.keys())))

gtfs_combinado = {}
for nome in todas_chaves:
    df_p = gtfs_p.get(nome, pd.DataFrame())
    df_s = gtfs_s.get(nome, pd.DataFrame())
    gtfs_combinado[nome] = merge_tabela(nome, df_p, df_s)

# 4. Aplicar clean_gtfs para remover órfãos
log_msg("Aplicando clean_gtfs para remover registros órfãos...")
gtfs_combinado = clean_gtfs(gtfs_combinado)

# 5. Estatísticas finais
log_msg("═══════════════════════════════════════════════════════════════")
log_msg("ESTATÍSTICAS DO GTFS COMBINADO:")
for k, v in gtfs_combinado.items():
    if v.empty:
        continue
    if k == 'shapes':
        log_msg(f"  ├─ shapes únicos: {v['shape_id'].nunique()}")
    else:
        log_msg(f"  ├─ {k}: {len(v)}")
log_msg("═══════════════════════════════════════════════════════════════")

# 6. Salvar
write_gtfs(gtfs_combinado, GTFS_SAIDA)

tempo_total = time.time() - tempo_inicio
print("\n╔════════════════════════════════════════════════════════════════════════════╗")
print("║                       PROCESSAMENTO FINALIZADO!                            ║")
print(f"║                    Tempo total: {tempo_total:.1f} segundos                             ║")
print("╚════════════════════════════════════════════════════════════════════════════╝\n")
