import pandas as pd
import zipfile
import os
import time
from pathlib import Path
import warnings

warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
INPUT_ZIPS = [
    r"C:/R_SMTR/dados/gtfs/2026/0128_gtfs_jun_26_2E_ret1.zip",
    r"C:/R_SMTR/dados/gtfs/2026/GTFS_Filtrado.zip",
]

OUTPUT_ZIP = r"C:/R_SMTR/dados/gtfs/2026/gtfs_combined.zip"

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def log_msg(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}")

def read_gtfs(zip_path):
    log_msg(f"Lendo: {zip_path}")
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
    log_msg(f"Salvando em: {zip_path}")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as zout:
        for key, df in gtfs_dict.items():
            if not df.empty:
                csv_bytes = df.to_csv(index=False).encode('utf-8')
                zout.writestr(f"{key}.txt", csv_bytes)

# ==============================================================================
# PROCESSAMENTO PRINCIPAL
# ==============================================================================
print("\n================================================================================")
print("                    CONCATENACAO SIMPLES DE GTFS")
print("================================================================================\n")

tempo_inicio = time.time()

gtfs_combined = {}

for zip_path in INPUT_ZIPS:
    if not os.path.exists(zip_path):
        log_msg(f"⚠ Arquivo não encontrado, pulando: {zip_path}")
        continue
    
    gtfs = read_gtfs(zip_path)
    
    for key, df in gtfs.items():
        if key not in gtfs_combined:
            gtfs_combined[key] = df
        else:
            gtfs_combined[key] = pd.concat([gtfs_combined[key], df], ignore_index=True)

# Drop duplicates per table
log_msg("Removendo duplicatas exatas por tabela...")
for key, df in gtfs_combined.items():
    if not df.empty:
        before = len(df)
        gtfs_combined[key] = df.drop_duplicates()
        after = len(gtfs_combined[key])
        if before != after:
            log_msg(f"  {key}: {before} -> {after} linhas ({before - after} duplicatas removidas)")

# Save
write_gtfs(gtfs_combined, OUTPUT_ZIP)

# Stats
log_msg("================================================================================")
log_msg("ESTATISTICAS DO GTFS COMBINADO:")
for k, v in gtfs_combined.items():
    if k == 'shapes':
        log_msg(f"  Shapes unicos:   {v['shape_id'].nunique() if 'shape_id' in v.columns else 'N/A'}")
    else:
        log_msg(f"  {k}:           {len(v)}")
log_msg("================================================================================")

tempo_total = time.time() - tempo_inicio
print(f"\n[OK] Concluido em {tempo_total:.1f} segundos")
print(f"[OK] Arquivo salvo em: {OUTPUT_ZIP}")