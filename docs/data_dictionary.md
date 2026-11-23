# Dicionário de Dados e Artefatos — Processar GTFS

Este documento cataloga os dados de entrada, insumos de referência, arquivos intermediários, entregáveis finais e artefatos temporários ou diagnósticos utilizados e produzidos pelo pipeline **Processar GTFS**.

Para detalhes de caminhos configuráveis e parâmetros de execução, consulte [configuration.md](./configuration.md). Para a ordem de execução das etapas, consulte [pipeline.md](./pipeline.md).

## Índice

- [1. Classificação do Ciclo de Vida dos Dados](#1-classificação-do-ciclo-de-vida-dos-dados)
- [2. Convenções de Nomenclatura](#2-convenções-de-nomenclatura)
- [3. Arquivos de Entrada e Insumos](#3-arquivos-de-entrada-e-insumos)
  - [3.1. GTFS ZIP Bruto](#31-gtfs-zip-bruto)
  - [3.2. Bases de Viagens GPS](#32-bases-de-viagens-gps)
  - [3.3. Insumos de Referência e Substituição](#33-insumos-de-referência-e-substituição)
  - [3.4. Tabela de Contagens de Partidas (Scripts `1.3` e `1.3.1`)](#34-tabela-de-contagens-de-partidas-scripts-13-e-131)
  - [3.5. Lista de Filtro de Trajetos Excepcionais (Script `9`)](#35-lista-de-filtro-de-trajetos-excepcionais-script-9)
- [4. Arquivos Intermediários](#4-arquivos-intermediários)
- [5. Arquivos Finais / Entregáveis](#5-arquivos-finais--entregáveis)
  - [5.1. GTFS Combinado e GTFS Público](#51-gtfs-combinado-e-gtfs-público)
  - [5.2. GTFS Atualizado com Quadros de Horários (`1.5` e `app_carregar_qh.py`)](#52-gtfs-atualizado-com-quadros-de-horários-15-e-app_carregar_qhpy)
  - [5.3. Workbooks Excel e Relatórios de Auditoria de QH](#53-workbooks-excel-e-relatórios-de-auditoria-de-qh)
  - [5.4. Camadas GIS (Trajetos e Pontos de Parada)](#54-camadas-gis-trajetos-e-pontos-de-parada)
  - [5.5. Listas de Partidas, Resumos, Extensões e Trajetos Alternativos](#55-listas-de-partidas-resumos-extensões-e-trajetos-alternativos)
- [6. Matriz de Relação Dados × Etapas do Pipeline](#6-matriz-de-relação-dados--etapas-do-pipeline)

---

## 1. Classificação do Ciclo de Vida dos Dados

| Categoria | Definição | Exemplos no Projeto | Política de Retenção |
|---|---|---|---|
| **Dados Persistentes (Entradas / Insumos)** | Fontes externas e tabelas de referência mantidas fora do código-fonte. Não são recriadas pelo pipeline. | GTFS brutos (`sppo_*.zip`, `brt_*.zip`, `rio_*.zip`), bases GPS (`viagens/`), `calendario.json`, `insumos/gtfs_cores.csv`, `insumos/trip_id_fantasma.txt`, `insumos/gtfs_combi/`, `insumos/gtfs_pub/`, `insumos_desvios/descricao_desvios.csv`, tabelas de contagens (`1.3`) e listas de filtro (`9`). | Persistente (sob `BASE_DADOS` ou pasta do estudo). |
| **Dados Intermediários (Regeneráveis)** | Artefatos produzidos por uma etapa e consumidos por etapas posteriores. Podem ser regerados a partir das entradas. | `*_PROC.zip` (Script `2`), `*_FILTRADO.zip` (Script `9`), `*_COMBINADO.zip` (Script `10`), CSVs de quadros de horários (`horarios_*.csv` de `1`, `1.2`, `1.3`, `1.4`). | Regenerável. |
| **Dados Finais (Entregáveis)** | Produtos destinados à publicação, análise gerencial, upload no Sigmob ou validação externa (`validacao_gtfs`). | `gtfs_combi_*.zip`, `gtfs_rio-de-janeiro_pub.zip`, `*_com_qh.zip` / `*_atualizado_qh.zip`, `quadros_partidas_*.xlsx`, `shapes_trajetos_*.{shp,gpkg}`, `shapes_pontos_*.{shp,gpkg}`, `partidas_*.{csv,parquet}`, `extensoes_*.csv`, `os_*_excep*.csv`, `tabela_domingo_ajustada.{xlsx,csv}`. | Entregável do estudo/publicação. |
| **Dados Temporários / Diagnósticos** | Arquivos efêmeros criados durante a execução ou relatórios emitidos apenas quando ocorrem inconsistências nos dados. | JSON temporário do [src/runner.py](../src/runner.py) (removido no `finally`), ZIPs temporários de upload da aba `5.2` (removidos no `finally`), `*_TEMP.zip` na substituição em `5`/`5.1`, `shape_dist_negativos.csv` (Script `2`), `relatorio_inconsistentes_YYYYMMDD_HHMMSS.csv` (Script `2`), `shapes_invalidos_com_trips.csv` (Script `6`). | Efêmero ou descarte após saneamento do erro. |

---

## 2. Convenções de Nomenclatura

O identificador de versão do estudo segue o sufixo `{YYYY}-{MM}-{NN}Q` (onde `{NN}` representa o número do estudo; a letra `Q` é mantida por retrocompatibilidade histórica).

### Arquivos GTFS (`.zip`)

| Padrão de Nome | Significado | Origem |
|---|---|---|
| `{modal}_{YYYY}-{MM}-{NN}Q.zip` | GTFS bruto de entrada (`modal` ∈ `sppo`, `brt`, `rio`). | Insumo externo (Sigmob) |
| `{modal}_{YYYY}-{MM}-{NN}Q_PROC.zip` | GTFS com `stop_times.txt` ajustado por GPS e `routes.txt` limpo. | Script `2` |
| `sppo_{YYYY}-{MM}-{NN}Q_FILTRADO.zip` | GTFS filtrado por lista de trajetos excepcionais. | Script `9` |
| `sppo_{YYYY}-{MM}-{NN}Q_COMBINADO.zip` | União com prioridade (`GTFS_PRINCIPAL` sobre `GTFS_SECUNDARIO`). | Script `10` |
| `gtfs_combi_{YYYY}-{MM}-{NN}Q.zip` | GTFS combinado operacional (mantém `EXCEP`). | Scripts `5`, `5.1` |
| `gtfs_rio-de-janeiro_pub.zip` | GTFS público final (sem `EXCEP`, com cores de `gtfs_cores.csv` aplicadas). | Scripts `5`, `5.1` |
| `gtfs_combi_{YYYY}-{MM}-{NN}Q_com_qh.zip` | GTFS base com quadros de horários (CSV) carregados via CLI/aba `1.5`. | Script `1.5` |
| `{stem_base}_atualizado_qh.zip` | GTFS base com quadros de horários carregados via app standalone. | [src/app_carregar_qh.py](../src/app_carregar_qh.py) |

### Quadros de Horários (`.csv` e `.xlsx`)

| Padrão de Nome | Significado | Origem |
|---|---|---|
| `horarios_{servico}_{headsign}_{service_id}.csv` | Quadro de horários por faixas de frequência (formato Sigmob, `trip_id` vazio). | Scripts `1`, `1.2`, `1.3`, `1.4` |
| `partidas_{servico}_{vista}_{calendario}.csv` | Grade de partidas detalhadas com ordem e intervalo em minutos. | Script `1.1` |
| `quadros_partidas_{service_id}.xlsx` | Workbook Excel consolidado (uma aba por serviço, blocos por sentido/headsign). | Scripts `1.3`, `1.4` |

### Produtos Finais (GIS, Partidas, Extensões e OS)

| Padrão de Nome | Significado | Origem |
|---|---|---|
| `shapes_trajetos_{YYYY}-{MM}-{NN}Q.{shp,gpkg}` | Camada vetorial de linhas (`LineString`) com atributos operacionais. | Script `6` |
| `shapes_pontos_{YYYY}-{MM}-{NN}Q.{shp,gpkg}` | Camada vetorial de pontos de parada (`Point`) ativos em `stop_times.txt`. | Script `6` |
| `partidas_{tipo_dia}.csv` | Partidas individuais por tipo de dia (`du`, `sab`, `dom`, `pf`) com coluna `intervalo`. | Script `7` |
| `partidas_{YYYY}-{MM}-{NN}Q.{csv,parquet}` | Consolidado de partidas de todos os tipos de dia processados. | Script `7` |
| `extensoes_{YYYY}-{MM}-{NN}Q.csv` / `extensoes_{sufixo}.csv` | Listagem de extensão máxima (metros inteiros, GIS) por serviço, vista e sentido. | Scripts `8`, `8.1` |
| `os_{YYYY}-{MM}-{NN}_excep*.csv` | Relatório de trajetos alternativos/excepcionais (OS). | Script `4` |

---

## 3. Arquivos de Entrada e Insumos

### 3.1. GTFS ZIP Bruto

Lido sempre com `dtype=str` para preservar zeros à esquerda em códigos de linha, parada e serviço. As 12 tabelas GTFS manipuladas pelo pipeline são:

| Tabela (`.txt`) | Campos Críticos Utilizados | Scripts Consumidores |
|---|---|---|
| `agency.txt` | `agency_id`, `agency_name` | `4`, `5`, `5.1`, `6`, `7`, `9`, `10`, `1.4` |
| `routes.txt` | `route_id`, `agency_id`, `route_short_name`, `route_long_name`, `route_type`, `route_color`, `route_text_color` | `1.4`, `2`, `4`, `5`, `5.1`, `6`, `7`, `8`, `8.1`, `9`, `10` |
| `trips.txt` | `trip_id`, `route_id`, `service_id`, `trip_headsign`, `trip_short_name`, `direction_id`, `shape_id` | Todos os scripts que leem GTFS |
| `stop_times.txt` | `trip_id`, `arrival_time`, `departure_time`, `stop_id`, `stop_sequence`, `shape_dist_traveled`, `timepoint` | `1.1`, `1.5`, `2`, `5`, `5.1`, `6`, `7`, `9`, `10` |
| `stops.txt` | `stop_id`, `stop_name`, `stop_lat`, `stop_lon`, `parent_station`, `location_type`, `stop_timezone`, `wheelchair_boarding`, `platform_code` | `5`, `5.1`, `6`, `9`, `10` |
| `shapes.txt` | `shape_id`, `shape_pt_lat`, `shape_pt_lon`, `shape_pt_sequence` | `4`, `5`, `5.1`, `6`, `7`, `8`, `8.1`, `9`, `10` |
| `calendar.txt` | `service_id`, dias da semana, `start_date`, `end_date` | `5`, `5.1`, `5.3`, `5.4`, `9`, `10`, `1.5` |
| `calendar_dates.txt` | `service_id`, `date`, `exception_type` | `5`, `5.1`, `5.3`, `5.4`, `9`, `10`, `1.5` |
| `frequencies.txt` | `trip_id`, `start_time`, `end_time`, `headway_secs` | `1`, `1.1`, `1.4`, `1.5`, `2`, `5`, `5.1`, `5.4`, `7`, `9`, `10` |
| `fare_attributes.txt` | `fare_id`, `price`, `currency_type` (padronizado para `"BRL"` em `5`/`5.1`) | `5`, `5.1`, `6`, `10` |
| `fare_rules.txt` | `fare_id`, `route_id` | `5`, `5.1`, `6`, `10` |
| `feed_info.txt` | Metadados do feed (reduzido a 1 linha em `5`/`5.1`) | `5`, `5.1`, `10` |

#### Regras de `route_type` Relevantes

| `route_type` | Modal / Classificação | Tratamento no Pipeline |
|---|---|---|
| `200` | Ônibus rodoviário / Frescão | Excluído nos Scripts `4` e `7`; recebe cor fixa `route_color="030478"` e `route_text_color="FFFFFF"` em `5`/`5.1`. |
| `700` | Ônibus convencional (SPPO) | Único tipo permitido por padrão no Script `1.4`; incluído em `8`/`8.1` (`['3', '700']`). |
| `702` | BRT (Expresso) | Cores originais preservadas em `5`/`5.1` (não sobrescritas por `gtfs_cores.csv`); incluído nas partidas do Script `7` e excluído da listagem só-SPPO de `8`/`8.1`. |
| `3` | Ônibus (padrão GTFS genérico) | Aceito em conjunto com `700` nos Scripts `8` e `8.1`. |

### 3.2. Bases de Viagens GPS

Consumidas exclusivamente pelo Script `2` ([codigos_py/2_ajustar_stop_times.py](../codigos_py/2_ajustar_stop_times.py)) para calcular velocidades médias reais por serviço, sentido, hora e tipo de dia (`U`, `S`, `D`):

| Modal | Localização sob `BASE_DADOS` | Formato | Campos Esperados | Observações |
|---|---|---|---|---|
| **SPPO / Rio** | `viagens/{sppo,rio}/{ano}/{mes}/` (recursivo) | `.parquet` | `servico` (ou `servico_informado`), `direction_id` (ou `sentido`: `I`→`0`, `V`→`1`, `C`→`0`), `datetime_partida`, `datetime_chegada`, `distancia_planejada` (km), `data` | Combinado com base de Frescão se existir. |
| **BRT** | `viagens/brt/{ano}/{mes}/validas/` (recursivo) | `.csv` | `servico`, `direction_id`, `datetime_partida`, `datetime_chegada`, `distancia_planejada` (m — dividido por `1000.0`), `data` | Leitura com `dtype=str`. |
| **Frescão** | `viagens/frescao/{ano}/{mes}/validas/` (recursivo) | `.csv` | `servico` (ou `servico_informado`), `direction_id`, `datetime_partida`, `datetime_chegada`, `distancia_planejada` (m — dividido por `1000.0`), `data` | Anexado automaticamente quando `gtfs_processar != "brt"`. |

### 3.3. Insumos de Referência e Substituição

| Arquivo / Pasta | Localização | Formato | Estrutura / Campos | Consumidores |
|---|---|---|---|---|
| `calendario.json` | `{BASE_DADOS}/calendario.json` | JSON | Objeto com chave `"holidays"` contendo lista de datas `"YYYY-MM-DD"` usadas para excluir feriados do cálculo de dia útil (`U`). | Script `2` |
| `gtfs_cores.csv` | `{BASE_DADOS}/insumos/gtfs_cores.csv` | CSV | Colunas obrigatórias: `route_short_name`, `route_color`, `route_text_color`. | Scripts `5`, `5.1` |
| `trip_id_fantasma.txt` | `{BASE_DADOS}/insumos/trip_id_fantasma.txt` | Texto (1 coluna, sem cabeçalho) | Um `trip_id` por linha a ser removido do GTFS/partidas. | Scripts `5`, `5.1`, `7` |
| `insumos/gtfs_combi/` | `{BASE_DADOS}/insumos/gtfs_combi/` (ou `.../RIO/<ETAPA>/`) | Diretório com `.txt` | Contém arquivos de substituição (`calendar_dates.txt`, `fare_attributes.txt`, `fare_rules.txt`, `feed_info.txt`) injetados no `gtfs_combi_*.zip`. | Scripts `5`, `5.1` |
| `insumos/gtfs_pub/` | `{BASE_DADOS}/insumos/gtfs_pub/` (ou `.../RIO/<ETAPA>/`) | Diretório com `.txt` | Contém os mesmos `.txt` de substituição injetados no `gtfs_rio-de-janeiro_pub.zip`. | Scripts `5`, `5.1` |
| `descricao_desvios.csv` | `<cwd>/insumos_desvios/descricao_desvios.csv` | CSV | Mapeamento de tag de desvio para texto descritivo (opcional no Script `6`; ausente = coluna `descricao_desvio` omitida). | Script `6` (e Script `3`, descontinuado) |

### 3.4. Tabela de Contagens de Partidas (Scripts `1.3` e `1.3.1`)

CSV em UTF-8 (ou Latin-1) com cabeçalhos normalizados automaticamente (minúsculas, sem acentos, espaços viram `_`). Aceita **dois formatos**:

1. **Formato longo:** uma linha por `(servico, sentido, faixa)` com colunas obrigatórias `servico`, `vista`, `sentido`, `faixa`, `partidas_faixa`.
2. **Formato *wide*:** uma linha por `(servico, sentido)` com colunas `servico`, `vista`, `sentido` mais até 14 colunas correspondentes às faixas padrão (`00:00-01:00`, `01:00-02:00`, ..., `06:00-09:00`, ..., `23:00-24:00`). O script detecta e aplica `melt` automaticamente para o formato longo.

Regras de validação:
- `sentido` deve pertencer a `{"Ida", "Volta", "Circular"}`.
- `vista` deve estar no formato `"Origem - Destino"` (exceto quando `sentido == "Circular"`), pois o `trip_headsign` é derivado da vista (`Destino` na Ida, `Origem` na Volta, `"Circular"` na Circular).
- Contagens aceitam inteiros ou decimais com vírgula/ponto (ex.: `"1,000"`, `"2.000"`), arredondadas para inteiro; `"-"` é tratado conforme `traco_ausente` (`"zerar"` ou `"erro"`).

### 3.5. Lista de Filtro de Trajetos Excepcionais (Script `9`)

CSV (separador `,`) ou TSV (separador `\t`, detectado automaticamente), proveniente da aba de alternativos da OS:

| Coluna | Mapeamento no GTFS | Papel no Filtro |
|---|---|---|
| `Serviço` | `trips.trip_short_name` | Obrigatória (chave de correspondência) |
| `Vista` | `routes.route_long_name` | Obrigatória (chave de correspondência) |
| `Consórcio` | `agency.agency_name` | Obrigatória (chave de correspondência) |
| `Sentido` | `trips.direction_id` (`Ida=0`, `Volta=1`) | Obrigatória (chave de correspondência) |
| `Evento` | Tag entre colchetes em `trips.trip_headsign` (ex.: `[desvio_feira]`) | Obrigatória (chave de correspondência) |
| `Extensão` | — | Informativa (não entra no critério de filtro) |

---

## 4. Arquivos Intermediários

### GTFS Processados e Filtrados

- **`{modal}_{YYYY}-{MM}-{NN}Q_PROC.zip`** (saída do Script `2`): cópia do GTFS de entrada substituindo `stop_times.txt` (com `shape_dist_traveled` normalizado a partir de `0`, horários recalculados por GPS com monotonicidade garantida) e `routes.txt` (sem rotas órfãs).
- **`sppo_{YYYY}-{MM}-{NN}Q_FILTRADO.zip`** (saída do Script `9`): subconjunto do GTFS contendo apenas as trips que atendem à lista de filtro e aos `CALENDARIOS_ALVO`, com limpeza em cascata (`clean_gtfs()`).

### CSVs de Quadros de Horários (`horarios_*.csv`)

Gerados pelos Scripts `1`, `1.2`, `1.3` e `1.4` e consumidos pelos Scripts `1.2`, `1.3.1`, `1.5` e por [src/app_carregar_qh.py](../src/app_carregar_qh.py).

Esquema padrão de **6 colunas** (formato de importação do **Sigmob**):

| Coluna Padrão | Tipo / Formato | Sinônimos Aceitos por `parse_qh_csv` (`1.5` / `app_carregar_qh.py`) | Observação |
|---|---|---|---|
| `trip_id` | `str` (vazio) | — | **Vazio (`""`) por design**: preenchido automaticamente ao subir o quadro no Sigmob e salvar. |
| `trip_headsign` | `str` | `headsign`, `vista`, `destino` | Sentido/destino do quadro. |
| `trip_short_name` | `str` | `servico`, `linha`, `route_short_name` | Código do serviço/linha. |
| `start_time` | `HH:MM:SS` (suporta `HH >= 24`) | `inicio`, `hora_inicio` | Início da banda de frequência. |
| `end_time` | `HH:MM:SS` (suporta `HH >= 24`) | `fim`, `hora_fim` | Fim da banda de frequência. |
| `headway_secs` | `int` (segundos) | `intervalo`, `headway` | Intervalo entre partidas consecutivas na banda. |

---

## 5. Arquivos Finais / Entregáveis

### 5.1. GTFS Combinado e GTFS Público

Produzidos pelos Scripts `5` e `5.1` em `{BASE_DADOS}/gtfs/{ano}/`:

- **`gtfs_combi_{YYYY}-{MM}-{NN}Q.zip`**: consolida os modais, remove pontos com `stop_name == "APAGAR"`, remove `trip_id_fantasma.txt`, padroniza `service_id` (`U`/`S`/`D` → `U_REG`/`S_REG`/`D_REG`), preenche `trip_headsign` vazio como `"Circular"`, define `timepoint = '0'`, define `currency_type = "BRL"`, aplica `clean_gtfs()` e injeta os `.txt` de `insumos/gtfs_combi/`. **Mantém viagens `EXCEP`.**
- **`gtfs_rio-de-janeiro_pub.zip`**: derivado do combinado com remoção de `service_id == "EXCEP"`, execução de `clean_gtfs()`, aplicação de cores de `gtfs_cores.csv` (preservando `route_type == '702'` e fixando `route_type == '200'`) e injeção dos `.txt` de `insumos/gtfs_pub/`.

### 5.2. GTFS Atualizado com Quadros de Horários (`1.5` e `app_carregar_qh.py`)

Produzido por [codigos_py/1.5_carregar_qh_no_gtfs.py](../codigos_py/1.5_carregar_qh_no_gtfs.py) (`*_com_qh.zip`) e [src/app_carregar_qh.py](../src/app_carregar_qh.py) (`*_atualizado_qh.zip`), ambos usando a lógica de [src/gtfs_carregar_qh.py](../src/gtfs_carregar_qh.py).

> **Invariante 1:1 `trips` / `frequencies`:** no modelo SMTR/Sigmob/dbt (`viagem_planejada_planejamento`), cada banda horária gravada em `frequencies.txt` **deve possuir seu próprio `trip_id` exclusivo** em `trips.txt` e `stop_times.txt`. O módulo nunca reutiliza o mesmo `trip_id` em múltiplas faixas (evitando falha no teste dbt `unique: [feed_start_date, id_viagem]`) e alinha o `departure_time` da primeira parada em `stop_times.txt` ao `start_time` da respectiva banda.

### 5.3. Workbooks Excel e Relatórios de Auditoria de QH

Gerados na pasta de saída dos Scripts `1.3`, `1.3.1` e `1.4`:

| Arquivo | Produtor | Estrutura / Conteúdo |
|---|---|---|
| `quadros_partidas_{service_id}.xlsx` | `1.3`, `1.4` | Uma aba por linha (`servico`); em cada aba, blocos por sentido/headsign com cabeçalho do quadro e tabela `Partida \| Horário \| Intervalo`. |
| `relatorio_bandas.csv` | `1.3`, `1.4` | Auditoria por banda gerada (`arquivo`, `servico`, `sentido`, `headsign`, `faixa`, `n_partidas`, `start_time`, `end_time`, `headway_secs` no `1.3`; campos equivalentes com agência/base no `1.4`). |
| `_resumo.txt` | `1.3`, `1.4` | Resumo textual consolidado com totais de entrada/saída, bandas, Excel e status do gate (`OK`). |
| `relatorio_conferencia_partidas.csv` | `1.3.1` | Conferência independente por célula e anomalia: `tipo`, `servico`, `sentido`, `headsign`, `faixa`, `n_entrada`, `n_quadro`, `detalhe`, `status` (`OK` ou `ANOMALIA` nos tipos `FALTANDO`, `SOBRANDO`, `ORFAO`, `BANDA`, `CELULA`, `EXCEL`). |
| `_conferencia_resumo.txt` | `1.3.1` | Resumo da conferência independente (acompanhado de código de saída `0` = OK ou `1` = falha). |

### 5.4. Camadas GIS (Trajetos e Pontos de Parada)

Geradas pelo Script `6` ([codigos_py/6_gerar_shapes.py](../codigos_py/6_gerar_shapes.py)) em `{BASE_DADOS}/shapes/{ano}/`, sempre em par **GeoPackage (`.gpkg`, nomes completos)** e **ESRI Shapefile (`.shp`, nomes truncados ao limite de 10 caracteres do formato DBF)**, em `EPSG:4326`:

- **`shapes_trajetos_{YYYY}-{MM}-{NN}Q.{gpkg,shp}`** (`LineString`):
  - Campos no `.gpkg`: `servico`, `destino`, `direcao`, `tipo_dia`, `extensao` (calculada em `EPSG:31983`), `consorcio`, `tipo_rota`, `descricao`, `tarifas`, `descricao_desvio` (omitida se não houver desvios ativos) e `geometry`.
  - Renomeação no `.shp`: `descricao_desvio` → `desvio`.
- **`shapes_pontos_{YYYY}-{MM}-{NN}Q.{gpkg,shp}`** (`Point`):
  - Paradas de `stops.txt` efetivamente referenciadas em `stop_times.txt`, acrescidas da coluna `route_type` (tipos de rota agregados separados por vírgula).
  - Renomeações no `.shp` (limite de 10 caracteres): `location_type` → `loc_type`, `parent_station` → `parent_sta`, `stop_timezone` → `timezone`, `wheelchair_boarding` → `wheelchair`, `platform_code` → `platform`.

### 5.5. Listas de Partidas, Resumos, Extensões e Trajetos Alternativos

| Artefato | Produtor | Localização Padrão | Colunas Principais |
|---|---|---|---|
| `partidas_{tipo_dia}.csv` | Script `7` | `{BASE_RESULTADOS}/partidas/` | `trip_short_name`, `trip_headsign`, `direction_id`, `departure_time`, `faixa`, `agency_name`, `extensao`, `route_type`, `tipo_dia`, `intervalo`. |
| `partidas_{sufixo}.{csv,parquet}` | Script `7` | `{BASE_RESULTADOS}/partidas/` | `trip_short_name`, `route_long_name`, `trip_headsign`, `direction_id`, `departure_time`, `faixa`, `agency_name`, `extensao`, `route_type`, `tipo_dia`. |
| `partidas_{servico}_{vista}_{calendario}.csv` | Script `1.1` | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_partidas_por_linha/{estudo}Q/` | `ordem_partida`, `trip_short_name`, `trip_headsign`, `service_id`, `direction_id`, `departure_time`, `intervalo_min`, `trip_id`. |
| `{nome_base_saida}.{xlsx,csv}` | Script `7.1` | `pasta_saida` configurada | `Serviço`, `Vista`, `Consórcio`, `Sentido`, `Extensão` seguidas de pares `Partidas <faixa> - Domingo` e `Quilometragem <faixa> - Domingo` (CSV separado por `;`, UTF-8 BOM). |
| `quadros_dom_*.csv` | Script `7.2` | `caminho_saida` configurado | Mesma estrutura de entrada (`quadros_du.csv`/`quadros_dom.csv`) com bloco `06:00`–`20:00` de dia útil combinado ao domingo. |
| `extensoes_*.csv` | Scripts `8`, `8.1` | `{BASE_RESULTADOS}/extensoes/` | `Serviço`, `Vista`, `Sentido`, `Extensão` (metros inteiros via GIS `EPSG:31983`, máximo por itinerário excluindo `EXCEP` e desvios `[`, filtrado para `route_type` em `['3', '700']`). |
| `os_*_excep*.csv` | Script `4` | `{BASE_DADOS}/os/` | `Serviço`, `Vista`, `Consórcio`, `Sentido`, `Extensão`, `Evento` (CSV separado por `,`, decimal `.`). |

---

## 6. Matriz de Relação Dados × Etapas do Pipeline

| Artefato / Dado | Categoria | Produzido por | Consumido por |
|---|---|---|---|
| GTFS bruto (`{modal}_{sufixo}.zip`) | Persistente | Externo (Sigmob) | `2` |
| Bases GPS (`viagens/`) + `calendario.json` | Persistente | Externo | `2` |
| GTFS processado (`*_PROC.zip`) | Intermediário | `2` | `4`, `5`, `5.1`, `7`, `9`, `10` |
| `insumos/gtfs_cores.csv`, `insumos/gtfs_combi/`, `insumos/gtfs_pub/` | Persistente | Externo | `5`, `5.1` |
| `insumos/trip_id_fantasma.txt` | Persistente | Externo | `5`, `5.1`, `7` |
| `insumos_desvios/descricao_desvios.csv` | Persistente | Externo | `6` (opcional) |
| GTFS filtrado (`*_FILTRADO.zip`) | Intermediário | `9` | `5.2`, `5.3`, `10` |
| GTFS combinado de prioridade (`*_COMBINADO.zip`) | Intermediário | `10` | `5`, `5.1` (ou uso direto) |
| `gtfs_combi_{sufixo}.zip` | Final | `5`, `5.1` | `1`, `1.1`, `1.4`, `1.5`, `5.2`, `5.3`, `5.4`, `7`, `app_format_qh.py`, `app_carregar_qh.py` |
| `gtfs_rio-de-janeiro_pub.zip` | Final | `5`, `5.1` | `6`, `8` |
| CSVs de QH (`horarios_*.csv`) | Intermediário / Final | `1`, `1.2`, `1.3`, `1.4`, `app_format_qh.py` | `1.2`, `1.3.1`, `1.5`, `app_carregar_qh.py`, Sigmob |
| Tabela de contagens de partidas (`.csv`) | Persistente | Externo / OS | `1.3`, `1.3.1` |
| `quadros_partidas_{service_id}.xlsx` | Final | `1.3`, `1.4` | `1.3.1`, análise gerencial |
| Relatórios de auditoria (`relatorio_bandas.csv`, `relatorio_conferencia_partidas.csv`, `_*resumo.txt`) | Final / Diagnóstico | `1.3`, `1.3.1`, `1.4` | Conferência operacional |
| GTFS com QH carregado (`*_com_qh.zip` / `*_atualizado_qh.zip`) | Final | `1.5`, `app_carregar_qh.py` | `7`, `8`, validação externa (`validacao_gtfs`) |
| Camadas GIS (`shapes_trajetos_*`, `shapes_pontos_*`) | Final | `6` | Ferramentas GIS (QGIS) / publicação |
| Partidas (`partidas_{tipo_dia}.csv`, `partidas_{sufixo}.{csv,parquet}`) | Final | `7` | `7.1`, `7.2`, validação externa (`validacao_gtfs`) |
| Resumo OS domingo (`tabela_domingo_ajustada.{xlsx,csv}`) e combinador (`quadros_dom_*.csv`) | Final | `7.1`, `7.2` | Emissão de OS |
| Extensões (`extensoes_*.csv`) | Final | `8`, `8.1` | Emissão de OS / conferência |
| Trajetos alternativos (`os_*_excep*.csv`) | Final | `4` | `9` (como lista de filtro), emissão de OS |
| Relatórios de erro (`shape_dist_negativos.csv`, `relatorio_inconsistentes_*.csv`, `shapes_invalidos_com_trips.csv`) | Temporário / Diagnóstico | `2`, `6` | Saneamento manual no Sigmob/GTFS |

---

## Documentação Relacionada

- [README.md](../README.md) — Visão geral, instalação e execução rápida.
- [architecture.md](./architecture.md) — Arquitetura da aplicação e decisões de projeto.
- [pipeline.md](./pipeline.md) — Fluxo completo de execução e dependências entre etapas.
- [scripts_reference.md](./scripts_reference.md) — Catálogo técnico de todos os scripts e módulos.
- [configuration.md](./configuration.md) — Dependências, parâmetros de execução, diretórios e constantes.
- [testing.md](./testing.md) — Testes automatizados e validações de consistência.
- [troubleshooting.md](./troubleshooting.md) — Diagnóstico e solução de problemas conhecidos.
