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
estudo_gtfs = _config.get("estudo_gtfs", "16") # ESTUDO, NÃO CONSIDERAR MAIS QUINZENA!!!!
sufixo      = f"{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q"

endereco_gtfs = Path(_config.get("endereco_gtfs", BASE_DADOS / f"gtfs/{ano_gtfs}/sppo_{sufixo}_PROC.zip"))
caminho_saida = Path(_config.get("caminho_saida", BASE_DADOS / f"gtfs/{ano_gtfs}/sppo_{sufixo}_FILTRADO.zip"))

# Filtrar por calendários específicos (service_id). Se vazio, utiliza todos.
# Exemplo: ["U", "S", "D", "EXCEP"]
CALENDARIOS_ALVO = _config.get("CALENDARIOS_ALVO", ["EXCEP"])
if isinstance(CALENDARIOS_ALVO, str):
    CALENDARIOS_ALVO = [x.strip() for x in CALENDARIOS_ALVO.split(',') if x.strip()]

# ==============================================================================
# LISTA DE FILTRO
# Colunas: Serviço | Vista | Consórcio | Sentido | Extensão | Evento
#
# A correspondência é feita por:
#   - Serviço   → trips.trip_short_name
#   - Vista     → routes.route_long_name
#   - Consórcio → agency.agency_name
#   - Sentido   → trips.direction_id  (Ida=0, Volta=1)
#   - Evento    → trips.trip_headsign (texto entre colchetes, ex: [desvio_feira])
#
# A coluna Extensão é usada apenas como referência e não entra no filtro.
# ==============================================================================
# A lista é proveniente da aba de alternativos da OS.
# Formato aceito: CSV separado por vírgula (,) ou TSV separado por tab (\t).
# O separador é detectado automaticamente em parse_lista_filtro().
_config_lista = _config.get("LISTA_FILTRO_RAW", None)
if _config_lista:
    LISTA_FILTRO_RAW = _config_lista
else:
    _lista_path = Path(_config.get(
        "LISTA_FILTRO_PATH",
        "C:/R_SMTR/resultados/lista_filtro/alternativos_155_faltam.csv"
    ))
    if _lista_path.exists():
        with open(_lista_path, 'r', encoding='utf-8') as _f:
            LISTA_FILTRO_RAW = _f.read()
    else:
        raise FileNotFoundError(f"Arquivo de lista de filtro não encontrado: {_lista_path}")

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


def clean_gtfs(gtfs_dict):
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


def parse_lista_filtro(raw_text: str) -> pd.DataFrame:
    """Lê o texto da lista de filtro e retorna um DataFrame normalizada.

    Aceita tanto CSV separado por vírgula (,) quanto TSV separado por tab (\\t).
    O separador é detectado automaticamente a partir da linha de cabeçalho.
    """
    text = raw_text.strip()
    # Detectar separador pela linha de cabeçalho: vírgula (CSV) ou tab (TSV)
    cabecalho = text.splitlines()[0] if text else ''
    if '\t' in cabecalho and cabecalho.count('\t') >= cabecalho.count(','):
        sep = '\t'
    else:
        sep = ','
    df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str)
    df.columns = df.columns.str.strip()

    # Mapear Sentido → direction_id numérico como string
    sentido_map = {"Ida": "0", "Volta": "1"}
    df['direction_id'] = df['Sentido'].map(sentido_map).fillna(df['Sentido'])

    df['Serviço']   = df['Serviço'].str.strip()
    df['Vista']     = df['Vista'].str.strip()
    df['Consórcio'] = df['Consórcio'].str.strip()
    df['Evento']    = df['Evento'].str.strip()

    return df


def extrair_evento(headsign_series: pd.Series) -> pd.Series:
    """Extrai o texto entre colchetes do trip_headsign, ex: '[desvio_feira]'."""
    return headsign_series.str.extract(r'(\[.*?\])')[0].fillna('')


# ==============================================================================
# PROCESSAMENTO PRINCIPAL
# ==============================================================================
print("\n╔════════════════════════════════════════════════════════════════════════════╗")
print("║              FILTRAR GTFS POR LISTA DE SERVIÇOS/EVENTOS                   ║")
print("╚════════════════════════════════════════════════════════════════════════════╝\n")

tempo_inicio = time.time()

# 1. Ler lista de filtro
log_msg("Processando lista de filtro...")
df_filtro = parse_lista_filtro(LISTA_FILTRO_RAW)
log_msg(f"  {len(df_filtro)} entradas na lista de filtro.")

# 2. Carregar GTFS
if not os.path.exists(endereco_gtfs):
    raise FileNotFoundError(f"Arquivo GTFS não encontrado: {endereco_gtfs}")

gtfs = read_gtfs(endereco_gtfs)

# 3. Filtrar por calendário, se especificado
df_trips  = gtfs.get('trips',  pd.DataFrame())
df_routes = gtfs.get('routes', pd.DataFrame())
df_agency = gtfs.get('agency', pd.DataFrame())

if df_trips.empty:
    raise ValueError("GTFS não contém trips.txt ou está vazio.")

if CALENDARIOS_ALVO:
    log_msg(f"Filtrando viagens para os calendários: {CALENDARIOS_ALVO}")
    df_trips = df_trips[df_trips['service_id'].isin(CALENDARIOS_ALVO)].copy()
    log_msg(f"  {len(df_trips)} trips após filtro de calendário.")

# 4. Enriquecer trips com route_long_name e agency_name para comparação
df_trips_rich = df_trips.merge(
    df_routes[['route_id', 'route_long_name', 'agency_id']],
    on='route_id', how='left'
)
df_trips_rich = df_trips_rich.merge(
    df_agency[['agency_id', 'agency_name']],
    on='agency_id', how='left'
)

# 5. Extrair evento do trip_headsign
df_trips_rich['evento'] = extrair_evento(df_trips_rich['trip_headsign'].fillna(''))

# 6. Construir chave de junção
#    (trip_short_name, route_long_name, agency_name, direction_id, evento)
SEP = '|||'
df_filtro['chave'] = (
    df_filtro['Serviço'] + SEP +
    df_filtro['Vista']   + SEP +
    df_filtro['Consórcio'] + SEP +
    df_filtro['direction_id'] + SEP +
    df_filtro['Evento']
)

df_trips_rich['chave'] = (
    df_trips_rich['trip_short_name'].fillna('').str.strip() + SEP +
    df_trips_rich['route_long_name'].fillna('').str.strip() + SEP +
    df_trips_rich['agency_name'].fillna('').str.strip()     + SEP +
    df_trips_rich['direction_id'].fillna('').str.strip()    + SEP +
    df_trips_rich['evento']
)

chaves_alvo = set(df_filtro['chave'])

# 7. Filtrar trips
trips_filtradas = df_trips_rich[df_trips_rich['chave'].isin(chaves_alvo)].copy()

# Verificar entradas da lista que não tiveram match
chaves_encontradas = set(trips_filtradas['chave'])
chaves_sem_match = chaves_alvo - chaves_encontradas
if chaves_sem_match:
    log_msg(f"⚠️  {len(chaves_sem_match)} entradas da lista NÃO tiveram match no GTFS:")
    df_sem_match = df_filtro[df_filtro['chave'].isin(chaves_sem_match)][
        ['Serviço', 'Vista', 'Consórcio', 'Sentido', 'Evento']
    ]
    for _, row in df_sem_match.iterrows():
        log_msg(f"   ✗ {row['Serviço']} | {row['Vista']} | {row['Consórcio']} | {row['Sentido']} | {row['Evento']}")
else:
    log_msg("✓ Todas as entradas da lista tiveram match no GTFS.")

log_msg(f"  {len(trips_filtradas)} trips selecionadas.")

if trips_filtradas.empty:
    log_msg("⛔ Nenhuma trip correspondeu à lista de filtro. Saindo sem gerar arquivo.")
    sys.exit(1)

# 8. Atualizar trips no dicionário GTFS (apenas colunas originais de trips.txt)
colunas_originais_trips = list(gtfs['trips'].columns)
gtfs['trips'] = trips_filtradas[
    [c for c in colunas_originais_trips if c in trips_filtradas.columns]
].copy()

# 9. Cascatear a remoção em todos os outros arquivos
log_msg("Aplicando clean_gtfs para remover registros órfãos...")
gtfs = clean_gtfs(gtfs)

# 10. Estatísticas finais
log_msg("═══════════════════════════════════════════════════════════════")
log_msg("ESTATÍSTICAS DO GTFS FILTRADO:")
for k, v in gtfs.items():
    if v.empty:
        continue
    if k == 'shapes':
        log_msg(f"  ├─ shapes únicos: {v['shape_id'].nunique()}")
    else:
        log_msg(f"  ├─ {k}: {len(v)}")
log_msg("═══════════════════════════════════════════════════════════════")

# 11. Salvar GTFS filtrado
write_gtfs(gtfs, caminho_saida)

tempo_total = time.time() - tempo_inicio
print("\n╔════════════════════════════════════════════════════════════════════════════╗")
print("║                       PROCESSAMENTO FINALIZADO!                            ║")
print(f"║                    Tempo total: {tempo_total:.1f} segundos                             ║")
print("╚════════════════════════════════════════════════════════════════════════════╝\n")
