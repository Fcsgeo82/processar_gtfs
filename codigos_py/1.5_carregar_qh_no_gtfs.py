import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Union

# Assegura stdout UTF-8 no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Adiciona raiz do repositório ao sys.path para importar src
_REPO_RAIZ = Path(__file__).resolve().parent.parent
if str(_REPO_RAIZ) not in sys.path:
    sys.path.insert(0, str(_REPO_RAIZ))

from src.gtfs_carregar_qh import (
    QuadroHorarioCSV,
    aplicar_quadros_gtfs,
    detectar_alteracoes,
    parse_qh_csv,
    read_gtfs,
    write_gtfs,
)

# ==============================================================================
# LEITURA DE CONFIGURAÇÃO (Linha de Comando / Streamlit / JSON)
# ==============================================================================
_parser = argparse.ArgumentParser(
    description="Carrega quadros de horários em formato CSV em um GTFS existente, substituindo as frequências correspondentes."
)
_parser.add_argument('--config', type=str, default='', help='Caminho para arquivo JSON de configuração')
_args, _ = _parser.parse_known_args()
_config = {}
if _args.config:
    if os.path.isfile(_args.config):
        with open(_args.config, 'r', encoding='utf-8-sig') as _f:
            _config = json.load(_f)
    else:
        try:
            _config = json.loads(_args.config)
        except Exception:
            with open(_args.config, 'r', encoding='utf-8-sig') as _f:
                _config = json.load(_f)

# Parâmetros principais
BASE_DADOS = Path(_config.get("BASE_DADOS", "C:/R_SMTR/dados"))
ano_gtfs = str(_config.get("ano_gtfs", "2026"))
mes_gtfs = str(_config.get("mes_gtfs", "11")).zfill(2)
estudo_gtfs = str(_config.get("estudo_gtfs", "04"))
sufixo = f"{ano_gtfs}-{mes_gtfs}-{estudo_gtfs}Q"

# Caminho do GTFS base
endereco_gtfs_base = Path(_config.get(
    "endereco_gtfs_base",
    BASE_DADOS / f"gtfs/{ano_gtfs}/gtfs_combi_{sufixo}_completo.zip"
))

# Caminho do GTFS de saída
caminho_saida = Path(_config.get(
    "caminho_saida",
    BASE_DADOS / f"gtfs/{ano_gtfs}/gtfs_combi_{sufixo}_com_qh.zip"
))

# Pasta ou lista de arquivos CSV de entrada
pasta_ou_arquivos = _config.get("arquivos_qh", "")
if not pasta_ou_arquivos:
    # Fallback para pasta padrão gerada pelo 1.3
    pasta_ou_arquivos = str(Path("C:/R_SMTR/resultados") / f"quadro_horario_extraido/{ano_gtfs}/{mes_gtfs}/qh_por_linha_partidas/{estudo_gtfs}Q")

service_id_fallback = str(_config.get("service_id_fallback", "F_REG"))
permitir_clonagem = bool(_config.get("permitir_clonagem", False))


def log_msg(msg: str):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}")


def coletar_arquivos_csv(origem: Union[str, List[str]]) -> List[Path]:
    """Coleta todos os arquivos CSV válidos a partir de um caminho, pasta ou lista."""
    caminhos: List[Path] = []
    if isinstance(origem, list):
        for item in origem:
            p = Path(item)
            if p.is_file() and p.suffix.lower() == ".csv":
                caminhos.append(p)
            elif p.is_dir():
                caminhos.extend(sorted(p.glob("*.csv")))
    elif isinstance(origem, str):
        p = Path(origem)
        if p.is_file() and p.suffix.lower() == ".csv":
            caminhos.append(p)
        elif p.is_dir():
            caminhos.extend(sorted(p.glob("*.csv")))
        elif "," in origem:
            for item in origem.split(","):
                cand = Path(item.strip())
                if cand.is_file() and cand.suffix.lower() == ".csv":
                    caminhos.append(cand)
    return caminhos


def main():
    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print("║            CARREGADOR DE QUADROS DE HORÁRIOS (CSV) NO GTFS                 ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")

    log_msg(f"GTFS Base de Entrada : {endereco_gtfs_base}")
    log_msg(f"GTFS de Saída        : {caminho_saida}")
    log_msg(f"Origem dos CSVs      : {pasta_ou_arquivos}")
    log_msg(f"Fallback service_id  : {service_id_fallback}")
    log_msg(f"Permitir Clonagem    : {'SIM' if permitir_clonagem else 'NÃO'}")

    if not endereco_gtfs_base.exists():
        raise FileNotFoundError(f"Arquivo GTFS base não encontrado: {endereco_gtfs_base}")

    # 1. Coletar e fazer parsing dos CSVs
    lista_caminhos = coletar_arquivos_csv(pasta_ou_arquivos)
    if not lista_caminhos:
        raise FileNotFoundError(f"Nenhum arquivo CSV de quadro horário encontrado em: {pasta_ou_arquivos}")

    log_msg(f"Coletando e validando {len(lista_caminhos)} arquivo(s) CSV...")
    quadros: List[QuadroHorarioCSV] = []
    for cp in lista_caminhos:
        try:
            qh = parse_qh_csv(cp, fallback_service_id=service_id_fallback)
            quadros.append(qh)
            log_msg(f"  ✔ {cp.name} -> Linha: {qh.servico} | Headsign: {qh.headsign} | Calendário: {qh.service_id} | Bandas: {qh.total_bandas} | Partidas: {qh.total_partidas}")
        except Exception as e:
            log_msg(f"  ⚠ Erro ao ler {cp.name}: {e}")

    if not quadros:
        raise ValueError("Nenhum quadro válido pôde ser lido a partir dos CSVs fornecidos.")

    # 2. Carregar GTFS base
    log_msg("Lendo tabelas do GTFS base...")
    gtfs = read_gtfs(endereco_gtfs_base)

    # 3. Detectar alterações e checar se há clonagens
    log_msg("Cruzando quadros com rotas e viagens do GTFS...")
    itens = detectar_alteracoes(gtfs, quadros)

    clonagens = [it for it in itens if it.status == "REQUER_CLONAGEM"]
    if clonagens:
        log_msg(f"⚠️ Atenção: {len(clonagens)} quadro(s) requerem clonagem de viagem molde:")
        for it in clonagens:
            log_msg(f"    - {it.quadro.servico} ({it.quadro.headsign}) para {it.quadro.service_id} (molde: {it.molde_service_id})")
        if not permitir_clonagem:
            raise PermissionError(
                f"A execução foi interrompida porque {len(clonagens)} quadro(s) exigem clonagem de viagens e a opção 'permitir_clonagem' está desativada. "
                "Para autorizar a clonagem, use permitir_clonagem=True na configuração."
            )

    # 4. Aplicar alterações no GTFS
    log_msg("Aplicando novas frequências no GTFS...")
    novo_gtfs, relatorio = aplicar_quadros_gtfs(gtfs, itens, permitir_clonagem=permitir_clonagem, logger=log_msg)

    # 5. Salvar GTFS modificado
    log_msg(f"Salvando novo GTFS em: {caminho_saida}")
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    write_gtfs(novo_gtfs, caminho_saida)

    # Resumo final
    sucessos = sum(1 for r in relatorio if r["status"] == "SUCESSO")
    partidas_totais = sum(r["partidas_inseridas"] for r in relatorio)
    print("\n╔════════════════════════════════════════════════════════════════════════════╗")
    print(f"║ PROCESSO CONCLUÍDO COM SUCESSO!                                            ║")
    print(f"║ Quadros aplicados: {sucessos}/{len(quadros)}                                              ║")
    print(f"║ Total de partidas registradas: {partidas_totais:<15,}                             ║")
    print(f"║ Arquivo gerado: {caminho_saida.name:<55}║")
    print("╚════════════════════════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
