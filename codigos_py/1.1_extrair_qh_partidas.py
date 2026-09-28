import os
import re
import json
import zipfile
import argparse
from pathlib import Path
import pandas as pd

# ==============================================================================
# LEITURA DE CONFIGURAÇÃO (Streamlit / Linha de Comando)
# ==============================================================================
_parser = argparse.ArgumentParser(description="Extrai quadro de horários com partidas detalhadas a partir do GTFS.")
_parser.add_argument('--config', type=str, default='', help='Caminho para arquivo JSON de configuração')
_args, _ = _parser.parse_known_args()
_config = {}
if _args.config:
    with open(_args.config, 'r', encoding='utf-8') as _f:
        _config = json.load(_f)

# Parâmetros principais
BASE_DADOS = Path(_config.get("BASE_DADOS", "C:/R_SMTR/dados"))
BASE_RESULTADOS = Path(_config.get("BASE_RESULTADOS", "C:/R_SMTR/resultados"))

ano_gtfs = _config.get("ano_gtfs", "2026")
mes_gtfs = _config.get("mes_gtfs", "09")
estudo_gtfs = _config.get("estudo_gtfs", "01")

# Caminho do GTFS (default: GTFS combinado do estudo/mês)
end_gtfs = Path(_config.get("end_gtfs", BASE_DADOS / f"gtfs/{ano_gtfs}/gtfs_combi_{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q.zip"))

# Linhas a rodar (se vazio ou ['todas'], processa todas as linhas do GTFS)
linhas_rodar = _config.get("linhas_rodar", ["804", "807", "809", "825", "840", "842", "849", "868", "870", "892", "898", "SN825", "SN840", "SN898", "808", "821", "822", "833", "841", "869", "893", "SN821", "SN893"])
if isinstance(linhas_rodar, str):
    linhas_rodar = [x.strip() for x in linhas_rodar.split(',') if x.strip()]

# Calendários / serviços a considerar
services_to_run = _config.get("services_to_run", ["U_REG", "S_REG", "D_REG"])
if isinstance(services_to_run, str):
    services_to_run = [x.strip() for x in services_to_run.split(',') if x.strip()]

# Pasta de saída dos arquivos por linha/sentido/dia
pasta_saida_config = _config.get("pasta_saida", "")
if pasta_saida_config:
    pasta_qh = Path(pasta_saida_config)
else:
    pasta_qh = BASE_RESULTADOS / f"quadro_horario_extraido/{ano_gtfs}/{mes_gtfs}/qh_partidas_por_linha/{estudo_gtfs}Q"

pasta_qh.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS
# ==============================================================================
def sanitize_filename(name: str) -> str:
    """Substitui caracteres inválidos para nomes de arquivos no sistema operacional."""
    if not name:
        return "SEM_NOME"
    # Substitui caracteres proibidos (\ / : * ? " < > |) por sublinhado
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', str(name))
    # Limpa espaços extras e pontos finais
    sanitized = re.sub(r'\s+', ' ', sanitized).strip('. ')
    return sanitized if sanitized else "SEM_NOME"

def horario_to_timedelta(hk_str):
    """Converte horário em formato HH:MM:SS ou HH:MM para Timedelta (suporta horas >= 24)."""
    if pd.isna(hk_str) or not str(hk_str).strip():
        return pd.NaT
    parts = str(hk_str).strip().split(':')
    if len(parts) < 2:
        return pd.NaT
    try:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) >= 3 else 0
        return pd.Timedelta(hours=h, minutes=m, seconds=s)
    except (ValueError, TypeError):
        return pd.NaT

def timedelta_to_horario(td):
    """Formata Timedelta para string HH:MM:SS mantendo suporte a horas >= 24."""
    if pd.isna(td):
        return ""
    total_seconds = int(td.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
print(f"Lendo GTFS de: {end_gtfs}")
if not os.path.exists(end_gtfs):
    raise FileNotFoundError(f"Arquivo GTFS não encontrado: {end_gtfs}")

with zipfile.ZipFile(end_gtfs, 'r') as z:
    file_list = z.namelist()
    
    if 'trips.txt' not in file_list:
        raise ValueError("Arquivo 'trips.txt' obrigatório não encontrado no GTFS.")
    
    with z.open('trips.txt') as f:
        trips = pd.read_csv(f, dtype=str)
    
    frequencies = pd.DataFrame()
    if 'frequencies.txt' in file_list:
        with z.open('frequencies.txt') as f:
            frequencies = pd.read_csv(f, dtype=str)
            
    stop_times = pd.DataFrame()
    if 'stop_times.txt' in file_list:
        with z.open('stop_times.txt') as f:
            # Carrega apenas colunas necessárias para economizar memória
            stop_times = pd.read_csv(f, dtype=str, usecols=lambda c: c in ['trip_id', 'stop_sequence', 'departure_time'])

print(f"  ✓ Trips carregadas: {len(trips)}")
print(f"  ✓ Frequencies carregadas: {len(frequencies)}")
print(f"  ✓ Stop times carregados: {len(stop_times)}")

# Garantir colunas essenciais em trips
for col in ['trip_id', 'trip_short_name', 'trip_headsign', 'service_id']:
    if col not in trips.columns:
        trips[col] = ""
if 'direction_id' not in trips.columns:
    trips['direction_id'] = ""

# Filtrar viagens por linhas solicitadas
if linhas_rodar and ('todas' not in [str(x).lower() for x in linhas_rodar]):
    trips_filtradas = trips[trips['trip_short_name'].isin(linhas_rodar)].copy()
else:
    trips_filtradas = trips.copy()

# Filtrar por calendários/serviços solicitados
if services_to_run and ('todos' not in [str(x).lower() for x in services_to_run]):
    trips_filtradas = trips_filtradas[trips_filtradas['service_id'].isin(services_to_run)].copy()

if trips_filtradas.empty:
    print("Nenhuma viagem atende aos filtros de linha e serviço especificados.")
    exit(0)

trips_ids_validos = set(trips_filtradas['trip_id'].unique())
print(f"  ✓ Viagens selecionadas para processamento: {len(trips_filtradas)} (de {trips_filtradas['trip_short_name'].nunique()} linhas)")

partidas_coletadas = []

# 1. PROCESSAR VIAGENS COM FREQUÊNCIA (frequencies.txt)
if not frequencies.empty:
    freq_filtradas = frequencies[frequencies['trip_id'].isin(trips_ids_validos)].copy()
    if not freq_filtradas.empty:
        freq_filtradas = freq_filtradas.merge(
            trips_filtradas[['trip_id', 'trip_short_name', 'trip_headsign', 'service_id', 'direction_id']],
            on='trip_id',
            how='inner'
        )
        
        freq_filtradas['start_td'] = freq_filtradas['start_time'].apply(horario_to_timedelta)
        freq_filtradas['end_td'] = freq_filtradas['end_time'].apply(horario_to_timedelta)
        freq_filtradas['headway_secs'] = pd.to_numeric(freq_filtradas['headway_secs'], errors='coerce').fillna(0).astype(int)
        
        viagens_freq_expandidas = []
        for _, row in freq_filtradas.iterrows():
            st = row['start_td']
            ed = row['end_td']
            hw_secs = row['headway_secs']
            if pd.isna(st) or pd.isna(ed) or hw_secs <= 0:
                continue
            
            hw = pd.Timedelta(seconds=hw_secs)
            current_time = st
            seq = 1
            while current_time < ed:
                viagens_freq_expandidas.append({
                    'trip_id': f"{row['trip_id']}_freq_{seq}",
                    'trip_short_name': row['trip_short_name'],
                    'trip_headsign': row['trip_headsign'],
                    'service_id': row['service_id'],
                    'direction_id': row['direction_id'],
                    'departure_td': current_time,
                    'origem': 'frequencies'
                })
                current_time += hw
                seq += 1
                
        if viagens_freq_expandidas:
            partidas_coletadas.extend(viagens_freq_expandidas)
            print(f"  ✓ Viagens expandidas por frequências: {len(viagens_freq_expandidas)}")

# Identificar trip_ids já cobertos por frequências
trips_com_frequencia = set(frequencies['trip_id'].unique()) if not frequencies.empty else set()

# 2. PROCESSAR VIAGENS REGULARES A PARTIR DE STOP_TIMES (para trips sem frequency)
if not stop_times.empty:
    trips_sem_freq = trips_filtradas[~trips_filtradas['trip_id'].isin(trips_com_frequencia)].copy()
    if not trips_sem_freq.empty:
        st_filtrado = stop_times[stop_times['trip_id'].isin(set(trips_sem_freq['trip_id']))].copy()
        if not st_filtrado.empty:
            st_filtrado['seq_int'] = pd.to_numeric(st_filtrado['stop_sequence'], errors='coerce').fillna(0).astype(int)
            # Ordena por trip_id e stop_sequence para obter o horário do primeiro ponto
            st_primeiro = st_filtrado.sort_values(by=['trip_id', 'seq_int']).drop_duplicates(subset=['trip_id'], keep='first')
            
            trips_regulares = st_primeiro.merge(
                trips_sem_freq[['trip_id', 'trip_short_name', 'trip_headsign', 'service_id', 'direction_id']],
                on='trip_id',
                how='inner'
            )
            
            trips_regulares['departure_td'] = trips_regulares['departure_time'].apply(horario_to_timedelta)
            trips_regulares = trips_regulares[trips_regulares['departure_td'].notna()].copy()
            
            for _, row in trips_regulares.iterrows():
                partidas_coletadas.append({
                    'trip_id': row['trip_id'],
                    'trip_short_name': row['trip_short_name'],
                    'trip_headsign': row['trip_headsign'],
                    'service_id': row['service_id'],
                    'direction_id': row['direction_id'],
                    'departure_td': row['departure_td'],
                    'origem': 'stop_times'
                })
            print(f"  ✓ Viagens regulares a partir de stop_times: {len(trips_regulares)}")

if not partidas_coletadas:
    print("Nenhuma partida pôde ser extraída com os parâmetros fornecidos.")
    exit(0)

df_partidas = pd.DataFrame(partidas_coletadas)

# ==============================================================================
# AGRUPAMENTO E GERAÇÃO DOS ARQUIVOS POR LINHA / SENTIDO / DIA
# ==============================================================================
grupos = df_partidas.groupby(['trip_short_name', 'trip_headsign', 'service_id'])

print(f"\nGerando arquivos de quadro de horários em: {pasta_qh}")
total_arquivos = 0

for (servico, vista, calendario), grupo in grupos:
    # Ordenar cronologicamente pelo horário de saída
    grupo_ordenado = grupo.sort_values(by='departure_td').reset_index(drop=True).copy()
    
    # Ordem da partida no dia (1, 2, 3...)
    grupo_ordenado['ordem_partida'] = grupo_ordenado.index + 1
    
    # Formatação do horário de partida
    grupo_ordenado['departure_time'] = grupo_ordenado['departure_td'].apply(timedelta_to_horario)
    
    # Cálculo do intervalo em relação à partida anterior (em minutos)
    diff_segundos = (grupo_ordenado['departure_td'] - grupo_ordenado['departure_td'].shift(1)).dt.total_seconds()
    intervalo_min = diff_segundos / 60.0
    
    # Para a 1ª viagem o intervalo é nulo; formatar com 1 casa decimal ou inteiro
    grupo_ordenado['intervalo_min'] = intervalo_min.apply(
        lambda x: "" if pd.isna(x) else (f"{int(x)}" if x == int(x) else f"{x:.1f}")
    )
    
    # Seleção e organização das colunas finais
    colunas_finais = [
        'ordem_partida',
        'trip_short_name',
        'trip_headsign',
        'service_id',
        'direction_id',
        'departure_time',
        'intervalo_min',
        'trip_id'
    ]
    df_saida = grupo_ordenado[colunas_finais]
    
    # Sanitização do nome do arquivo
    servico_str = sanitize_filename(servico)
    vista_str = sanitize_filename(vista)
    calendario_str = sanitize_filename(calendario)
    
    nome_arquivo = f"partidas_{servico_str}_{vista_str}_{calendario_str}.csv"
    caminho_arquivo = pasta_qh / nome_arquivo
    
    df_saida.to_csv(caminho_arquivo, index=False, encoding='utf-8')
    total_arquivos += 1

print(f"\n==========================================================")
print(f"PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
print(f"Total de combinações (arquivos gerados): {total_arquivos}")
print(f"Total de partidas exportadas: {len(df_partidas)}")
print(f"Pasta de destino: {pasta_qh}")
print(f"==========================================================\n")
