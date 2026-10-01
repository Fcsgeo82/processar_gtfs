import pandas as pd
import zipfile
import io
import os
from pathlib import Path

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

# Parameters
BASE_DADOS = Path(_config.get("BASE_DADOS", "C:/R_SMTR/dados"))
BASE_RESULTADOS = Path(_config.get("BASE_RESULTADOS", "C:/R_SMTR/resultados"))

ano_gtfs = _config.get("ano_gtfs", "2029")
mes_gtfs = _config.get("mes_gtfs", "10")
estudo_gtfs = _config.get("estudo_gtfs", "01") #ESTUDO, NÃO CONSIDERAR MAIS QUINZENA!!!!

# GTFS file path
end_gtfs = Path(_config.get("end_gtfs", BASE_DADOS / f"gtfs/{ano_gtfs}/gtfs_combi_{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q.zip"))

# Read GTFS (frequencies and trips) directly from the ZIP file
# We'll use pandas to read the specific CSVs from within the zip archive
print(f"Lendo arquivo GTFS de: {end_gtfs}")

with zipfile.ZipFile(end_gtfs, 'r') as z:
    with z.open('frequencies.txt') as f:
        frequencies = pd.read_csv(f)
    with z.open('trips.txt') as f:
        trips = pd.read_csv(f)

# Lines to run
linhas_rodar = _config.get("linhas_rodar", ["007", "014", "100", "104", "107", "109", "117", "133", "157", "160", "161", "162", "165", "167", "169", "201", "202", "209", "217", "229", "232", "238", "247", "249", "254", "292", "296", "298", "301", "302", "306", "312", "313", "315", "319", "324", "326", "328", "329", "335", "341", "342", "343", "348", "350", "353", "355", "361", "362", "363", "368", "369", "371", "378", "383", "384", "386", "388", "390", "393", "397", "399", "409", "410", "415", "422", "426", "448", "455", "456", "457", "461", "472", "473", "474", "476", "483", "492", "497", "507", "518", "519", "539", "550", "552", "553", "554", "557", "565", "583", "584", "600", "601", "603", "606", "607", "608", "610", "611", "613", "614", "616", "621", "622", "623", "624", "625", "627", "628", "629", "630", "636", "638", "639", "650", "651", "652", "653", "665", "669", "678", "679", "685", "687", "688", "691", "692", "696", "711", "712", "721", "731", "737", "741", "743", "745", "746", "753", "754", "756", "759", "764", "765", "766", "770", "771", "774", "775", "778", "779", "780", "783", "785", "786", "788", "790", "791", "793", "794", "796", "798", "799", "801", "802", "803", "810", "812", "817", "819", "820", "830", "831", "834", "835", "836", "837", "838", "843", "845", "846", "847", "848", "850", "851", "852", "853", "854", "855", "857", "859", "861", "862", "863", "864", "865", "866", "867", "871", "872", "878", "880", "881", "883", "884", "885", "894", "895", "897", "900", "901", "905", "906", "908", "910", "913", "915", "917", "918", "919", "920", "922", "925", "926", "928", "932", "940", "944", "946", "950", "951", "954", "959", "979", "987", "990", "LECD126", "LECD133", "LECD134", "LECD136", "LECD138", "LECD150", "LECD151", "LECD153", "LECD154", "LECD155", "LECD156", "LECD157", "LECD158", "SP265", "SP759", "SP795", "SP805", "SP864", "SP918", "SV319", "SV474", "SV606", "SV624", "SV669", "SV774", "SV777", "SV790", "SV831", "SV853", "SV863", "SV866", "SV878", "SV908", "SV917", "SV922", "SVA665", "SVB665", "SVB685"])
if isinstance(linhas_rodar, str):
    linhas_rodar = [x.strip() for x in linhas_rodar.split(',') if x.strip()]

# Em vez de apenas linhas específicas, como ["249"], podemos pegar todas as linhas únicas do arquivo trips
# linhas_rodar = trips['trip_short_name'].unique().tolist()
services_to_run = _config.get("services_to_run", ["U_REG","S_REG", "D_REG"]) # 

# Process trips first: keep only needed columns and filter by requested lines
trips_filtered = trips[['trip_id', 'trip_short_name', 'trip_headsign', 'service_id']]

# Join frequencies with trips
# frequencies_desvios <- left_join(gtfs$frequencies, select(gtfs$trips, ...))
frequencias_desvios = pd.merge(frequencies, trips_filtered, on='trip_id', how='left')

# Filter
# filter(trip_short_name %in% linhas_rodar) %>% filter(service_id %in% c("S_REG", "D_REG"))
frequencias_desvios = frequencias_desvios[
    (frequencias_desvios['trip_short_name'].isin(linhas_rodar)) & 
    (frequencias_desvios['service_id'].isin(services_to_run))
]

# linhas_processar: distinct trip_short_name, trip_headsign, service_id
# arrange(trip_short_name, desc(service_id))
linhas_processar = frequencias_desvios[['trip_short_name', 'trip_headsign', 'service_id']]\
    .drop_duplicates()\
    .sort_values(by=['trip_short_name', 'service_id'], ascending=[True, False])

# Define the output directory based on R script
pasta_qh = BASE_RESULTADOS / f"quadro_horario_extraido/{ano_gtfs}/{mes_gtfs}/qh_por_linha/{estudo_gtfs}Q/"
# R equivalent to dir.create:
os.makedirs(pasta_qh, exist_ok=True)

print(f"Serão processados os seguintes serviços:\n{linhas_processar}")

# Iterate through distinct rows and save files
for index, row in linhas_processar.iterrows():
    servico = row['trip_short_name']
    vista = row['trip_headsign']
    calendario = row['service_id']
    
    # Filter the joined dataframe based on current row
    quadro_linha = frequencias_desvios[
        (frequencias_desvios['trip_short_name'] == servico) &
        (frequencias_desvios['trip_headsign'] == vista) &
        (frequencias_desvios['service_id'] == calendario)
    ].copy()
    
    # Arrange by start_time
    quadro_linha = quadro_linha.sort_values(by='start_time')
    
    # Mutate trip_id = "" and select specific columns
    quadro_linha['trip_id'] = ""
    quadro_linha = quadro_linha[['trip_id', 'trip_headsign', 'trip_short_name', 'start_time', 'end_time', 'headway_secs']]
    
    nome_arq = f"horarios_{servico}_{vista}_{calendario}.csv"
    caminho_arquivo = pasta_qh / nome_arq
    
    print(f"Salvando: {caminho_arquivo}")
    # Write to CSV
    quadro_linha.to_csv(caminho_arquivo, index=False)

print("Processamento concluído.")