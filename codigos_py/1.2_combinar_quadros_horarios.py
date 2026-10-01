import os
import re
import json
import argparse
from pathlib import Path
import pandas as pd

# ==============================================================================
# LEITURA DE CONFIGURAÇÃO (Linha de Comando / Streamlit / JSON)
# ==============================================================================
_parser = argparse.ArgumentParser(
    description="Combina quadros de horários entre diferentes serviços/calendários com recorte por faixa de horário."
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

# Parâmetros principais
BASE_DADOS = Path(_config.get("BASE_DADOS", "C:/R_SMTR/dados"))
BASE_RESULTADOS = Path(_config.get("BASE_RESULTADOS", "C:/R_SMTR/resultados"))

ano_gtfs = str(_config.get("ano_gtfs", "2029"))
mes_gtfs = str(_config.get("mes_gtfs", "10")).zfill(2)
estudo_gtfs = str(_config.get("estudo_gtfs", "01"))

# Serviços e horários de corte
servico_origem = str(_config.get("servico_origem", "U_REG"))      # Ex.: Dia Útil
servico_destino = str(_config.get("servico_destino", "D_REG"))    # Ex.: Domingo
hora_inicio = str(_config.get("hora_inicio", "06:00:00"))         # Início do bloco a importar
hora_fim = str(_config.get("hora_fim", "20:00:00"))               # Fim do bloco a importar (exclusivo)

# Linhas a rodar (se vazio ou ['todas'], processa todas as linhas encontradas)
linhas_rodar = _config.get("linhas_rodar", ["007", "014", "100", "104", "107", "109", "117", "133", "157", "160", "161", "162", "165", "167", "169", "201", "202", "209", "217", "229", "232", "238", "247", "249", "254", "292", "296", "298", "301", "302", "306", "312", "313", "315", "319", "324", "326", "328", "329", "335", "341", "342", "343", "348", "350", "353", "355", "361", "362", "363", "368", "369", "371", "378", "383", "384", "386", "388", "390", "393", "397", "399", "409", "410", "415", "422", "426", "448", "455", "456", "457", "461", "472", "473", "474", "476", "483", "492", "497", "507", "518", "519", "539", "550", "552", "553", "554", "557", "565", "583", "584", "600", "601", "603", "606", "607", "608", "610", "611", "613", "614", "616", "621", "622", "623", "624", "625", "627", "628", "629", "630", "636", "638", "639", "650", "651", "652", "653", "665", "669", "678", "679", "685", "687", "688", "691", "692", "696", "711", "712", "721", "731", "737", "741", "743", "745", "746", "753", "754", "756", "759", "764", "765", "766", "770", "771", "774", "775", "778", "779", "780", "783", "785", "786", "788", "790", "791", "793", "794", "796", "798", "799", "801", "802", "803", "810", "812", "817", "819", "820", "830", "831", "834", "835", "836", "837", "838", "843", "845", "846", "847", "848", "850", "851", "852", "853", "854", "855", "857", "859", "861", "862", "863", "864", "865", "866", "867", "871", "872", "878", "880", "881", "883", "884", "885", "894", "895", "897", "900", "901", "905", "906", "908", "910", "913", "915", "917", "918", "919", "920", "922", "925", "926", "928", "932", "940", "944", "946", "950", "951", "954", "959", "979", "987", "990", "LECD126", "LECD133", "LECD134", "LECD136", "LECD138", "LECD150", "LECD151", "LECD153", "LECD154", "LECD155", "LECD156", "LECD157", "LECD158", "SP265", "SP759", "SP795", "SP805", "SP864", "SP918", "SV319", "SV474", "SV606", "SV624", "SV669", "SV774", "SV777", "SV790", "SV831", "SV853", "SV863", "SV866", "SV878", "SV908", "SV917", "SV922", "SVA665", "SVB665", "SVB685"])
if isinstance(linhas_rodar, str):
    linhas_rodar = [x.strip() for x in linhas_rodar.split(',') if x.strip()]
linhas_rodar_set = {str(x).upper() for x in linhas_rodar} if linhas_rodar and ('todas' not in [str(x).lower() for x in linhas_rodar]) else set()

# Pastas de entrada e saída
pasta_entrada_config = _config.get("pasta_entrada", "")
if pasta_entrada_config:
    pasta_entrada = Path(pasta_entrada_config)
else:
    pasta_entrada = BASE_RESULTADOS / f"quadro_horario_extraido/{ano_gtfs}/{mes_gtfs}/qh_por_linha/{estudo_gtfs}Q"

pasta_saida_config = _config.get("pasta_saida", "")
if pasta_saida_config:
    pasta_saida = Path(pasta_saida_config)
else:
    pasta_saida = BASE_RESULTADOS / f"quadro_horario_extraido/{ano_gtfs}/{mes_gtfs}/qh_por_linha_combinado/{estudo_gtfs}Q"

pasta_saida.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS DE HORÁRIO E ARQUIVOS
# ==============================================================================
def horario_to_seconds(hk_str) -> int:
    """Converte horário HH:MM:SS ou HH:MM para total de segundos (suporta H >= 24)."""
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

def seconds_to_horario(total_seconds: int) -> str:
    """Converte total de segundos de volta para string HH:MM:SS mantendo H >= 24."""
    if total_seconds < 0:
        return ""
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def sanitize_filename(name: str) -> str:
    """Substitui caracteres inválidos para nomes de arquivos no sistema operacional."""
    if not name:
        return "SEM_NOME"
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', str(name))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip('. ')
    return sanitized if sanitized else "SEM_NOME"

def parse_filename(file_path: Path):
    """
    Identifica serviço (linha), vista (destino) e calendário a partir do nome do arquivo.
    Suporta padrões:
      - horarios_{servico}_{vista}_{calendario}.csv (ex: horarios_804_Campo Grande_D_REG.csv)
      - qh_{servico}-{vista}_{calendario}.csv (ex: qh_378-Castelo_D.csv)
    """
    stem = file_path.stem
    candidatos = [servico_origem, servico_destino, "U_REG", "S_REG", "D_REG", "U", "S", "D"]
    candidatos_ordenados = sorted(list(set(candidatos)), key=len, reverse=True)

    if stem.startswith("horarios_"):
        conteudo = stem[len("horarios_"):]
        if '_' in conteudo:
            servico, resto = conteudo.split('_', 1)
            for cand in candidatos_ordenados:
                if resto.endswith(f"_{cand}"):
                    vista = resto[:-len(f"_{cand}")]
                    return servico, vista, cand
            if '_' in resto:
                vista, calendario = resto.rsplit('_', 1)
                return servico, vista, calendario
            return servico, resto, ""
    elif stem.startswith("qh_"):
        conteudo = stem[len("qh_"):]
        for cand in candidatos_ordenados:
            if conteudo.endswith(f"_{cand}"):
                resto = conteudo[:-len(f"_{cand}")]
                if '-' in resto:
                    subparts = resto.split('-', 1)
                    return subparts[0], subparts[1], cand
                return resto, "GERAL", cand
        if '_' in conteudo:
            resto, calendario = conteudo.rsplit('_', 1)
            if '-' in resto:
                subparts = resto.split('-', 1)
                return subparts[0], subparts[1], calendario
            return resto, "GERAL", calendario

    return None, None, None

# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
print(f"==========================================================")
print(f"COMBINAÇÃO DE QUADROS DE HORÁRIOS")
print(f"Pasta de Entrada : {pasta_entrada}")
print(f"Pasta de Destino : {pasta_saida}")
print(f"Serviço Origem   : {servico_origem} (importar faixa)")
print(f"Serviço Destino  : {servico_destino} (quadro a ser atualizado/gerado)")
print(f"Janela Horária   : {hora_inicio} até {hora_fim} (exclusivo)")
if linhas_rodar_set:
    print(f"Linhas Filtradas : {len(linhas_rodar_set)} linhas especificadas")
else:
    print(f"Linhas Filtradas : Todas as linhas encontradas")
print(f"==========================================================\n")

if not pasta_entrada.exists():
    raise FileNotFoundError(f"Pasta de entrada não encontrada: {pasta_entrada}")

t_inicio = horario_to_seconds(hora_inicio)
t_fim = horario_to_seconds(hora_fim)

if t_inicio < 0 or t_fim < 0 or t_inicio >= t_fim:
    raise ValueError(f"Intervalo de horário inválido: {hora_inicio} até {hora_fim}")

# 1. Mapear arquivos existentes na pasta de entrada
arquivos_origem = {}   # (servico, vista) -> Path
arquivos_destino = {}  # (servico, vista) -> Path

for f in pasta_entrada.glob("*.csv"):
    servico, vista, calendario = parse_filename(f)
    if not servico:
        continue
    
    # Se houver filtro de linhas, aplica
    if linhas_rodar_set and servico.upper() not in linhas_rodar_set:
        continue
    
    chave = (servico, vista)
    if calendario == servico_origem:
        arquivos_origem[chave] = f
    elif calendario == servico_destino:
        arquivos_destino[chave] = f

todas_chaves = sorted(list(set(arquivos_origem.keys()) | set(arquivos_destino.keys())))

if not todas_chaves:
    print("Nenhum arquivo correspondente aos critérios foi encontrado na pasta de entrada.")
    exit(0)

print(f"Total de combinações (linha + vista) identificadas: {len(todas_chaves)}")
print(f"  - Com arquivo de origem ({servico_origem}) : {len(arquivos_origem)}")
print(f"  - Com arquivo de destino ({servico_destino}): {len(arquivos_destino)}\n")

total_gerados = 0

for servico, vista in todas_chaves:
    faixas_finais = []
    
    # --------------------------------------------------------------------------
    # A. Carregar faixas do serviço de destino original (se existir)
    # --------------------------------------------------------------------------
    arq_dest = arquivos_destino.get((servico, vista))
    if arq_dest and arq_dest.exists():
        df_dest = pd.read_csv(arq_dest, dtype=str)
        for _, row in df_dest.iterrows():
            st_sec = horario_to_seconds(row.get('start_time'))
            ed_sec = horario_to_seconds(row.get('end_time'))
            hw = row.get('headway_secs', '')
            
            if st_sec < 0 or ed_sec < 0 or st_sec >= ed_sec:
                continue
            
            # Caso 1: Madrugada integralmente antes de t_inicio
            if ed_sec <= t_inicio:
                faixas_finais.append({
                    'trip_id': '',
                    'trip_headsign': row.get('trip_headsign', vista),
                    'trip_short_name': row.get('trip_short_name', servico),
                    'start_time': row.get('start_time'),
                    'end_time': row.get('end_time'),
                    'headway_secs': hw,
                    '_st_sec': st_sec
                })
            # Caso 2: Madrugada cruzando a fronteira de t_inicio
            elif st_sec < t_inicio < ed_sec:
                faixas_finais.append({
                    'trip_id': '',
                    'trip_headsign': row.get('trip_headsign', vista),
                    'trip_short_name': row.get('trip_short_name', servico),
                    'start_time': row.get('start_time'),
                    'end_time': seconds_to_horario(t_inicio),
                    'headway_secs': hw,
                    '_st_sec': st_sec
                })
            
            # Caso 3: Noite integralmente após t_fim
            if st_sec >= t_fim:
                faixas_finais.append({
                    'trip_id': '',
                    'trip_headsign': row.get('trip_headsign', vista),
                    'trip_short_name': row.get('trip_short_name', servico),
                    'start_time': row.get('start_time'),
                    'end_time': row.get('end_time'),
                    'headway_secs': hw,
                    '_st_sec': st_sec
                })
            # Caso 4: Noite cruzando a fronteira de t_fim
            elif st_sec < t_fim < ed_sec:
                faixas_finais.append({
                    'trip_id': '',
                    'trip_headsign': row.get('trip_headsign', vista),
                    'trip_short_name': row.get('trip_short_name', servico),
                    'start_time': seconds_to_horario(t_fim),
                    'end_time': row.get('end_time'),
                    'headway_secs': hw,
                    '_st_sec': t_fim
                })
    
    # --------------------------------------------------------------------------
    # B. Importar faixas do serviço de origem na janela [t_inicio, t_fim)
    # --------------------------------------------------------------------------
    arq_orig = arquivos_origem.get((servico, vista))
    if arq_orig and arq_orig.exists():
        df_orig = pd.read_csv(arq_orig, dtype=str)
        for _, row in df_orig.iterrows():
            st_sec = horario_to_seconds(row.get('start_time'))
            ed_sec = horario_to_seconds(row.get('end_time'))
            hw = row.get('headway_secs', '')
            
            if st_sec < 0 or ed_sec < 0 or st_sec >= ed_sec:
                continue
            
            # Verifica se sobrepõe a janela [t_inicio, t_fim)
            if ed_sec <= t_inicio or st_sec >= t_fim:
                continue
            
            # Recorta (clipping) nas bordas
            clipped_st = max(st_sec, t_inicio)
            clipped_ed = min(ed_sec, t_fim)
            
            if clipped_ed > clipped_st:
                faixas_finais.append({
                    'trip_id': '',
                    'trip_headsign': row.get('trip_headsign', vista),
                    'trip_short_name': row.get('trip_short_name', servico),
                    'start_time': seconds_to_horario(clipped_st),
                    'end_time': seconds_to_horario(clipped_ed),
                    'headway_secs': hw,
                    '_st_sec': clipped_st
                })
    
    if not faixas_finais:
        continue
    
    # --------------------------------------------------------------------------
    # C. Ordenação e formatação final idêntica ao Script 1
    # --------------------------------------------------------------------------
    df_saida = pd.DataFrame(faixas_finais)
    df_saida = df_saida.sort_values(by='_st_sec').reset_index(drop=True)
    
    colunas_finais = ['trip_id', 'trip_headsign', 'trip_short_name', 'start_time', 'end_time', 'headway_secs']
    df_saida = df_saida[colunas_finais]
    
    # Nome do arquivo sanitizado no formato do Script 1
    servico_str = sanitize_filename(servico)
    vista_str = sanitize_filename(vista)
    nome_arquivo = f"horarios_{servico_str}_{vista_str}_{servico_destino}.csv"
    caminho_arquivo = pasta_saida / nome_arquivo
    
    df_saida.to_csv(caminho_arquivo, index=False, encoding='utf-8')
    total_gerados += 1

print(f"==========================================================")
print(f"PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
print(f"Total de quadros de horários gerados: {total_gerados}")
print(f"Pasta de destino: {pasta_saida}")
print(f"==========================================================\n")
