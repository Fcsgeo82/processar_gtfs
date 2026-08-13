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
estudo_gtfs = _config.get("estudo_gtfs", "08") # ESTUDO, NÃO CONSIDERAR MAIS QUINZENA!!!!
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
# A lista é proveniente da aba de alternativos da OS
LISTA_FILTRO_RAW = _config.get("LISTA_FILTRO_RAW", """Serviço\tVista\tConsórcio\tSentido\tExtensão\tEvento
104\tSão Conrado - Terminal Gentileza\tIntersul\tIda\t27.085\t[desvio_feira]
104\tSão Conrado - Terminal Gentileza\tIntersul\tVolta\t26.369\t[desvio_feira]
107\tCentral - Urca\tIntersul\tIda\t12.468\t[desvio_obras]
133\tLargo do Machado - Terminal Gentileza\tIntersul\tIda\t9.448\t[excepcionalidade]
133\tLargo do Machado - Terminal Gentileza\tIntersul\tVolta\t12.740\t[excepcionalidade]
161\tTerminal Gentileza - Ipanema\tIntersul\tIda\t27.355\t[desvio_feira]
167\tTerminal Gentileza - Urca\tIntersul\tIda\t14.780\t[desvio_tunel]
167\tTerminal Gentileza - Urca\tIntersul\tVolta\t17.418\t[desvio_tunel]
169\tTerminal Gentileza - General Osório\tIntersul\tIda\t17.474\t[desvio_aterro]
169\tTerminal Gentileza - General Osório\tIntersul\tVolta\t19.926\t[desvio_aterro]
169\tTerminal Gentileza - General Osório\tIntersul\tIda\t16.783\t[desvio_tunel_e_desvio_aterro]
169\tTerminal Gentileza - General Osório\tIntersul\tVolta\t20.779\t[desvio_tunel_e_desvio_aterro]
169\tTerminal Gentileza - General Osório\tIntersul\tIda\t17.408\t[desvio_tunel]
169\tTerminal Gentileza - General Osório\tIntersul\tVolta\t20.142\t[desvio_tunel]
201\tSanta Alexandrina - Castelo\tIntersul\tIda\t7.136\t[desvio_lazer]
201\tSanta Alexandrina - Castelo\tIntersul\tIda\t6.153\t[excepcionalidade]
201\tSanta Alexandrina - Castelo\tIntersul\tVolta\t7.340\t[excepcionalidade]
202\tRio Comprido - Castelo\tIntersul\tIda\t8.308\t[excepcionalidade]
202\tRio Comprido - Castelo\tIntersul\tVolta\t9.012\t[excepcionalidade]
249\tÁgua Santa - Carioca\tInternorte\tIda\t18.745\t[desvio_maracana]
361\tRecreiro dos Bandeirantes - Castelo\tTranscarioca\tIda\t47.517\t[excepcionalidade]
361\tRecreiro dos Bandeirantes - Castelo\tTranscarioca\tVolta\t45.942\t[excepcionalidade]
371\tPraça Seca - Praça Tiradentes\tTranscarioca\tVolta\t28.312\t[desvio_maracana]
371\tPraça Seca - Praça Tiradentes\tTranscarioca\tVolta\t29.512\t[desvio_lazer]
371\tPraça Seca - Praça Tiradentes\tTranscarioca\tIda\t26.412\t[excepcionalidade]
410\tSaens Peña - Gávea\tIntersul\tIda\t19.438\t[excepcionalidade]
410\tSaens Peña - Gávea\tIntersul\tVolta\t20.818\t[excepcionalidade]
426\tUsina - Jardim de Alah\tIntersul\tIda\t22.282\t[excepcionalidade]
426\tUsina - Jardim de Alah\tIntersul\tVolta\t23.799\t[excepcionalidade]
553\tRecreiro dos Bandeirantes - Rio Sul\tTranscarioca\tIda\t41.505\t[excepcionalidade]
553\tRecreiro dos Bandeirantes - Rio Sul\tTranscarioca\tVolta\t38.749\t[excepcionalidade]
624\tMariópolis - Praça da Bandeira\tInternorte\tIda\t35.231\t[eventos_climaticos]
624\tMariópolis - Praça da Bandeira\tInternorte\tVolta\t39.039\t[eventos_climaticos]
665\tPavuna - Saens Peña\tInternorte\tVolta\t27.542\t[desvio_feira]
665\tPavuna - Saens Peña\tInternorte\tIda\t34.140\t[desvio_maracana_2]
838\tTerminal Campo Grande - Terminal Magarça\tSanta Cruz\tIda\t13.990\t[eventos_climaticos]
838\tTerminal Campo Grande - Terminal Magarça\tSanta Cruz\tVolta\t13.331\t[eventos_climaticos]
910\tBananal - Irajá\tInternorte\tIda\t27.023\t[excepcionalidade_1]
910\tBananal - Irajá\tInternorte\tIda\t27.353\t[excepcionalidade_2]
913\tDel Castilho - Fundão\tInternorte\tIda\t16.808\t[excepcionalidade]
913\tDel Castilho - Fundão\tInternorte\tVolta\t10.769\t[excepcionalidade]
917\tPadre Miguel - Bonsucesso\tInternorte\tVolta\t29.034\t[eventos_climaticos]
917\tPadre Miguel - Bonsucesso\tInternorte\tVolta\t29.163\t[eventos_climaticos_1]
917\tPadre Miguel - Bonsucesso\tInternorte\tVolta\t29.427\t[excepcionalidade]
919\tPavuna - Bonsucesso\tInternorte\tIda\t21.273\t[excepcionalidade]
920\tPavuna - Bonsucesso\tInternorte\tIda\t19.234\t[excepcionalidade]
920\tPavuna - Bonsucesso\tInternorte\tVolta\t18.135\t[excepcionalidade]
961\tRio das Pedras - Recreio dos Bandeirantes\tTranscarioca\tIda\t27.431\t[excepcionalidade]
961\tRio das Pedras - Recreio dos Bandeirantes\tTranscarioca\tVolta\t24.336\t[excepcionalidade]
LECD131\tSão Conrado - Terminal Gentileza\tIntersul\tIda\t24.599\t[excepcionalidade]
LECD147\tMetrô Pavuna - Saens Peña\tInternorte\tVolta\t33.080\t[desvio_feira]
LECD147\tMetrô Pavuna - Saens Peña\tInternorte\tIda\t33.455\t[desvio_maracana_2]
LECD151\tGrajaú - Leblon\tIntersul\tIda\t24.452\t[desvio_maracana_e_tunel]
SN232\tLins de Vasconcelos - Castelo\tInternorte\tIda\t18.034\t[desvio_maracana]
SN265\tMarechal Hermes - Castelo\tInternorte\tVolta\t32.588\t[desvio_tunel]
SN624\tMariópolis - Praça da República\tInternorte\tIda\t42.500\t[eventos_climaticos]
SN624\tMariópolis - Praça da República\tInternorte\tVolta\t41.516\t[eventos_climaticos]
SV624\tMariópolis - Praça da Bandeira\tInternorte\tIda\t36.541\t[eventos_climaticos]
SV624\tMariópolis - Praça da Bandeira\tInternorte\tVolta\t43.511\t[eventos_climaticos]
SV917\tPadre Miguel - Bonsucesso\tInternorte\tVolta\t29.318\t[eventos_climaticos]
SVB665\tPavuna - Saens Peña\tInternorte\tIda\t33.897\t[desvio_maracana_2]
SVB665\tPavuna - Saens Peña\tInternorte\tIda\t34.270\t[excepcionalidade]
SVB665\tPavuna - Saens Peña\tInternorte\tVolta\t28.518\t[excepcionalidade]
"""

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
    """Lê o texto TSV da lista de filtro e retorna um DataFrame normalizado."""
    df = pd.read_csv(io.StringIO(raw_text.strip()), sep='\t', dtype=str)
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
