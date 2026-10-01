import os
import json
import argparse
from pathlib import Path
import pandas as pd

# ==============================================================================
# LEITURA DE CONFIGURAÇÃO (Linha de Comando / Streamlit / JSON)
# ==============================================================================
_parser = argparse.ArgumentParser(
    description="Gera tabela resumo de partidas por faixa horária para Domingo (importando Dia Útil das 06h às 20h)."
)
_parser.add_argument('--config', type=str, default='', help='Caminho para arquivo JSON de configuração')
_args, _ = _parser.parse_known_args()
_config = {}
if _args.config:
    if os.path.isfile(_args.config):
        with open(_args.config, 'r', encoding='utf-8') as _f:
            _config = json.load(_f)
    else:
        try:
            _config = json.loads(_args.config)
        except Exception:
            with open(_args.config, 'r', encoding='utf-8') as _f:
                _config = json.load(_f)

# Parâmetros de Entrada e Saída
caminho_entrada = Path(_config.get(
    "caminho_entrada",
    r"C:\R_SMTR\resultados\OS_historico\2026_SET_1ºESTUDO_RETIFICAÇÃO\partidas\partidas_2026-09-01Q.parquet"
))

pasta_saida = Path(_config.get(
    "pasta_saida",
    r"C:\R_SMTR\resultados\OS_historico\2026_SET_1ºESTUDO_RETIFICAÇÃO\arquivos_os"
))

nome_base_saida = str(_config.get("nome_base_saida", "tabela_domingo_ajustada"))

hora_inicio = str(_config.get("hora_inicio", "06:00:00"))
hora_fim = str(_config.get("hora_fim", "20:00:00"))

# ==============================================================================
# FUNÇÕES UTILITÁRIAS
# ==============================================================================
def horario_para_segundos(hk_str) -> int:
    """Converte horário HH:MM:SS para segundos inteiros (suporta horas >= 24)."""
    if pd.isna(hk_str) or not str(hk_str).strip():
        return -1
    parts = str(hk_str).strip().split(':')
    if len(parts) < 2:
        return -1
    try:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) >= 3 else 0
        return h * 3600 + m * 60 + s
    except (ValueError, TypeError):
        return -1

# ==============================================================================
# PROCESSAMENTO
# ==============================================================================
print("==========================================================")
print("GERADOR DE RESUMO DE PARTIDAS (DOMINGO COM DIA ÚTIL 06h-20h)")
print(f"Arquivo de Entrada : {caminho_entrada}")
print(f"Pasta de Saída     : {pasta_saida}")
print(f"Janela de Dia Útil : {hora_inicio} até {hora_fim} (exclusivo)")
print("==========================================================\n")

if not caminho_entrada.exists():
    raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho_entrada}")

pasta_saida.mkdir(parents=True, exist_ok=True)

# 1. Carregamento dos dados
print("1. Carregando dados de partidas...")
if caminho_entrada.suffix.lower() == '.parquet':
    df = pd.read_parquet(caminho_entrada)
else:
    df = pd.read_csv(caminho_entrada, dtype=str)

print(f"   [OK] Total de viagens carregadas: {len(df):,}")

# 2. Filtragem de horários
print("2. Aplicando filtro de calendário e faixa horária...")
df['dep_sec'] = df['departure_time'].apply(horario_para_segundos)

t_inicio = horario_para_segundos(hora_inicio)
t_fim = horario_para_segundos(hora_fim)

# Regra:
# - Dia Útil (du) no intervalo [hora_inicio, hora_fim)
# - Domingo (dom) fora desse intervalo (< hora_inicio ou >= hora_fim)
mask_du = (df['tipo_dia'] == 'du') & (df['dep_sec'] >= t_inicio) & (df['dep_sec'] < t_fim)
mask_dom = (df['tipo_dia'] == 'dom') & ((df['dep_sec'] < t_inicio) | (df['dep_sec'] >= t_fim))

df_sel = df[mask_du | mask_dom].copy()
print(f"   [OK] Viagens selecionadas: {len(df_sel):,}")
print(f"     - De Dia Útil ({hora_inicio} às {hora_fim}): {mask_du.sum():,}")
print(f"     - De Domingo (madrugada e noite): {mask_dom.sum():,}")

# 3. Definição das 14 faixas horárias padrão
faixas_ordem = [
    '00:00-01:00', '01:00-02:00', '02:00-03:00', '03:00-04:00', '04:00-05:00', '05:00-06:00',
    '06:00-09:00', '09:00-12:00', '12:00-15:00', '15:00-18:00', '18:00-21:00', '21:00-22:00',
    '22:00-23:00', '23:00-24:00'
]

# 4. Agrupamento e Tabela Dinâmica
print("3. Agrupando e pivotando por faixa horária...")
colunas_chave = ['trip_short_name', 'trip_headsign', 'agency_name', 'direction_id', 'extensao']

pivot = df_sel.pivot_table(
    index=colunas_chave,
    columns='faixa',
    values='departure_time',
    aggfunc='count',
    fill_value=0
).reset_index()

# Renomeia colunas de identificação
rename_map = {
    'trip_short_name': 'Serviço',
    'trip_headsign': 'Vista',
    'agency_name': 'Consórcio',
    'direction_id': 'Sentido',
    'extensao': 'Extensão'
}
pivot.rename(columns=rename_map, inplace=True)

# 5. Organização final das colunas intercalando Partidas e Quilometragem em branco
cols_finais = ['Serviço', 'Vista', 'Consórcio', 'Sentido', 'Extensão']
for f in faixas_ordem:
    col_part = f'Partidas {f} - Domingo'
    col_km = f'Quilometragem {f} - Domingo'
    
    if f in pivot.columns:
        pivot[col_part] = pivot[f]
    else:
        pivot[col_part] = 0
        
    pivot[col_km] = ''  # Quilometragem em branco conforme solicitado
    cols_finais.extend([col_part, col_km])

df_resultado = pivot[cols_finais].sort_values(by=['Serviço', 'Sentido']).reset_index(drop=True)

# 6. Gravação dos arquivos (Excel e CSV)
arquivo_xlsx = pasta_saida / f"{nome_base_saida}.xlsx"
arquivo_csv = pasta_saida / f"{nome_base_saida}.csv"

print(f"\n4. Gravando arquivos de saída:")
print(f"   - Excel : {arquivo_xlsx}")
df_resultado.to_excel(arquivo_xlsx, index=False)

print(f"   - CSV   : {arquivo_csv}")
df_resultado.to_csv(arquivo_csv, index=False, sep=';', encoding='utf-8-sig')

print(f"\n==========================================================")
print("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
print(f"Total de registros gerados: {len(df_resultado):,}")
print(f"Total de colunas: {len(df_resultado.columns)}")
print("==========================================================\n")
