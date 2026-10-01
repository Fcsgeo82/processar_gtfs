# Memória de longo prazo — Processar GTFS

Registro de decisões, histórico e contexto detalhado. Complementa o `AGENTS.md`.
Preferência: adicionar entradas no topo, datadas.

---

## 2026-10-01 — Script combinador de partidas (7.2) e atualização de doc

- Criado `codigos_py/7.2_combinador_partidas.py` (a partir do protótipo
  `combinador_quadros.py`): combina partidas de tipos de dia diferentes no
  formato do arquivo de partidas gerado pelo script 7.
  - Mantém apenas serviços presentes em `partidas_dom`; madrugada (<06h) e noite
    (>=20h) do Domingo, bloco diurno (06h–20h) do Dia Útil.
  - Compatibiliza o campo `intervalo` nas transições 05:59→06:00 e 19:59→20:00.
  - Entrada default: `quadros_du.csv` / `quadros_dom.csv`; saída `quadros_dom_04-10.csv`.
- Documentação atualizada: `README.md` (seções 7.1 e 7.2 e nota do pipeline),
  `CHANGELOG.md` e `AGENTS.md`. Descrição do 7.1 reforçada como combinação de
  partidas de diferentes tipos de dia no formato da tabela de OS.

---

## 2026-09-28 — Criação do script de resumo de OS de domingo com dia útil (7.1)

- Criado `codigos_py/7.1_resumo_os_domingo_du.py` para processar a base consolidada de partidas
  (`partidas_YYYY-MM-QQ.parquet` ou `.csv` gerados pelo script 7) e gerar tabela resumo por faixa horária.
- Regra de composição de Domingo:
  - Partidas entre 06:00:00 e 20:00:00 (exclusivo) importadas de Dia Útil (`tipo_dia == 'du'`).
  - Partidas fora do intervalo (< 06:00:00 ou >= 20:00:00) mantidas de Domingo (`tipo_dia == 'dom'`).
- Agrupa por `(Serviço, Vista, Consórcio, Sentido, Extensão)` e pivota pelas 14 faixas horárias padrão,
  intercalando contagem de partidas e colunas de quilometragem em branco.
- Exporta tanto em Excel (`.xlsx`) quanto em CSV (`utf-8-sig`, separador `;`).
- Arquivos gerados e validados em `C:\R_SMTR\resultados\OS_historico\2026_SET_1ºESTUDO_RETIFICAÇÃO\arquivos_os\tabela_domingo_ajustada.*`.

---

## 2026-09-28 — Criação do script de combinação de quadros de horários (1.2)

- Criado `codigos_py/1.2_combinar_quadros_horarios.py` para mesclar quadros de horários
  entre serviços/calendários com recorte por faixa horária.
- Caso de uso inicial: gerar quadros de domingo (`D_REG`) aproveitando as faixas de dia útil
  (`U_REG`) entre 06:00:00 e 20:00:00 (exclusivo).
- Consome diretamente os arquivos de faixas do script `1` (`qh_por_linha`), preservando a estrutura
  original de intervalos (`start_time`, `end_time`, `headway_secs`).
- Lógica de clipping e substituição:
  - Preserva faixas de domingo de madrugada (`< 06:00:00`) e noite (`>= 20:00:00`), ajustando bordas.
  - Importa faixas de dia útil no intervalo `[06:00:00, 20:00:00)`.
  - Se a linha não tiver domingo original, gera o domingo a partir da faixa de dia útil.
  - Ordena cronologicamente por `start_time` e exporta no mesmo formato do script 1 (`horarios_*.csv`).
- Parâmetros configuráveis via `--config <json>` ou string JSON inline: `servico_origem`, `servico_destino`,
  `hora_inicio`, `hora_fim`, `linhas_rodar`, `pasta_entrada`, `pasta_saida`.
- Validado com dados reais da linha 378 (cortes precisos às 06h e 20h preservando cabeçalho e colunas).

---

## 2026-09-28 — Criação do script de extração de QH por partidas (1.1)

- Criado `codigos_py/1.1_extrair_qh_partidas.py` para extrair grade detalhada de partidas
  a partir do GTFS.
- Suporta tanto viagens com faixas em `frequencies.txt` (expansão cronológica) quanto viagens
  regulares em `stop_times.txt` (partida no primeiro ponto da rota).
- Gera atributos analíticos essenciais: `ordem_partida` (1, 2, 3...) e `intervalo_min` (diferença
  em minutos em relação à partida anterior).
- Exporta CSVs individuais organizados por `trip_short_name`, `trip_headsign` e `service_id`,
  com sanitização de caracteres proibidos no Windows para nomes de arquivos.
- Mantém padrão com suporte a `--config <json>` e fallback para parâmetros hardcoded.
- Validado com sucesso em dados reais (GTFS combinado `gtfs_combi_2026-09-01Q.zip`), gerando 123 arquivos e 5.969 partidas exportadas para 23 linhas.

---

## 2026-08-27 — Criação do banco de memória

- Criados `AGENTS.md` e `.opencode/memory.md`.
- Projeto central da SMTR: pipeline completo de processamento de GTFS do Rio de
  Janeiro (SPPO, BRT e Rio), do ajuste de horários por GPS até exportações GIS.
- Stack: Python (pandas, numpy, geopandas, shapely, pyogrio, pyarrow, loguru,
  tqdm) + Streamlit. Existe ainda um `.Rproj` com código R antigo em `codigos_R/`
  (pasta `datados/` contém versões sem uso).
- Fluxo principal: 0 validar → 2 ajustar ST → 5 juntar (ou 9/10 para
  excepcionalidades) → 6 shapes / 7 partidas / 8 extensões.
- `src/runner.py`: rodando via Streamlit, os scripts recebem `--config <json>`
  gerado temporariamente; sem o argumento usam hardcodes no topo do arquivo.
- Script `0_validar_gtfs_entrada` faz validações de padrão de `trip_headsign`
  (excepcionalidades `[...]`) e retorna exit code específico.
- Script `5_juntar_gtfs` cuida da versão pública `gtfs_rio-de-janeiro_pub.zip` e
  interna `gtfs_combi_YYYY-MM-QQ.zip`; variantes 5.1/5.2/5.3/5.4 cobrem casos
  específicos (modal único, concatenação simples, substituição de linhas,
  eliminação de duplicatas preservando EXCEP).
- Seqüência histórica de refatoração: pipeline original em R foi portado para
  Python; a interface Streamlit veio depois (com abas por script).
- Pontos de atenção: `Iniciar_App.bat` inicializa a aplicação; `stop_times.csv`
  na raiz é dado de trabalho, não código.