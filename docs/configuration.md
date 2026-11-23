# Configurações do Projeto — Processar GTFS

Este documento detalha as dependências, variáveis de ambiente, mecanismo de parametrização (`--config`), estrutura de diretórios, parâmetros de cada etapa e constantes técnicas utilizadas no pipeline **Processar GTFS**.

Para visão geral do fluxo de processamento, consulte [pipeline.md](./pipeline.md). Para o catálogo completo de scripts, consulte [scripts_reference.md](./scripts_reference.md).

## Índice

- [1. Dependências e Ambiente Python](#1-dependências-e-ambiente-python)
- [2. Variáveis de Ambiente](#2-variáveis-de-ambiente)
- [3. Mecanismo `--config <json>` e Precedência](#3-mecanismo---config-json-e-precedência)
- [4. Parâmetros Globais da Interface (`src/app.py`)](#4-parâmetros-globais-da-interface-srcapppy)
- [5. Estrutura de Diretórios de Entrada, Saída e Insumos](#5-estrutura-de-diretórios-de-entrada-saída-e-insumos)
- [6. Parâmetros de Execução por Etapa / Script](#6-parâmetros-de-execução-por-etapa--script)
  - [Etapa 1 — Quadros de Horários (Scripts 1 a 1.5)](#etapa-1--quadros-de-horários-scripts-1-a-15)
  - [Etapa 2 — Ajustar Stop Times (Script 2)](#etapa-2--ajustar-stop-times-script-2)
  - [Etapa 4 — Trajetos Alternativos (Script 4)](#etapa-4--trajetos-alternativos-script-4)
  - [Etapa 5 — Junção e Deduplicação de GTFS (Scripts 5 a 5.4)](#etapa-5--junção-e-deduplicação-de-gtfs-scripts-5-a-54)
  - [Etapa 6 — Gerar Shapes GIS (Script 6)](#etapa-6--gerar-shapes-gis-script-6)
  - [Etapa 7 — Lista e Combinação de Partidas (Scripts 7 a 7.2)](#etapa-7--lista-e-combinação-de-partidas-scripts-7-a-72)
  - [Etapa 8 — Gerar Extensões (Scripts 8 e 8.1)](#etapa-8--gerar-extensões-scripts-8-e-81)
  - [Etapa 9 — Filtrar GTFS por Lista (Script 9)](#etapa-9--filtrar-gtfs-por-lista-script-9)
  - [Etapa 10 — Juntar Dois GTFS com Prioridade (Script 10)](#etapa-10--juntar-dois-gtfs-com-prioridade-script-10)
- [7. Constantes Técnicas Relevantes](#7-constantes-técnicas-relevantes)

---

## 1. Dependências e Ambiente Python

O projeto utiliza um ambiente virtual local (`.venv`) validado em **Python 3.13+**. As dependências são declaradas em [requirements.txt](../requirements.txt) sem versões fixadas (*unpinned*):

| Pacote | Finalidade Principal no Projeto |
|---|---|
| `pandas` | Leitura, junção, agregação e exportação de tabelas GTFS (CSV/TXT) e planilhas. |
| `numpy` | Operações vetorizadas, tratamento de `NaN` e cálculos numéricos de tempo/distância. |
| `geopandas` | Construção de `GeoDataFrame`, reprojeção de CRS (`EPSG:4326` → `EPSG:31983`) e exportação GIS. |
| `shapely` | Criação de geometrias `LineString` (shapes/trajetos) e `Point` (pontos de parada). |
| `pyogrio` | Engine de leitura/escrita geoespacial usada na geração de `.shp` e `.gpkg` no Script 6. |
| `pyarrow` | Leitura das bases de viagens GPS em Parquet (Script 2) e escrita de partidas consolidadas em Parquet (Script 7). |
| `loguru` | Biblioteca de logging listada nas dependências do projeto. |
| `tqdm` | Barra de progresso em utilitários de linha de comando. |
| `streamlit` | Interface web principal ([src/app.py](../src/app.py)) e aplicativos standalone ([src/app_format_qh.py](../src/app_format_qh.py), [src/app_carregar_qh.py](../src/app_carregar_qh.py)). |
| `openpyxl` | Geração e conferência de workbooks Excel (`.xlsx`) nos Scripts `1.3`, `1.3.1`, `1.4` e `7.1`. |

### Atalho de Inicialização (`Iniciar_App.bat`)

O arquivo [Iniciar_App.bat](../Iniciar_App.bat), na raiz do repositório, automatiza a inicialização da aplicação principal no Windows:

1. Ativa o ambiente virtual com `call .venv\Scripts\activate.bat`.
2. Executa `python -m streamlit run src/app.py`.

Para os aplicativos standalone, o comando equivalente com o ambiente virtual ativo é:

```powershell
python -m streamlit run src/app_format_qh.py
python -m streamlit run src/app_carregar_qh.py
```

---

## 2. Variáveis de Ambiente

O projeto **não utiliza arquivo `.env`** nem exige variáveis de ambiente externas para execução.

A única variável configurada em tempo de execução é definida automaticamente pelo executor [src/runner.py](../src/runner.py) antes de disparar cada subprocesso:

| Variável | Valor | Onde é Definida | Finalidade |
|---|---|---|---|
| `PYTHONIOENCODING` | `"utf-8"` | [src/runner.py](../src/runner.py) (`sub_env["PYTHONIOENCODING"] = "utf-8"`) | Força `stdin`/`stdout`/`stderr` em UTF-8 nos subprocessos, evitando `UnicodeEncodeError` no console Windows (codepage padrão `cp1252`) ao imprimir caracteres de caixa (`╔═╗`, `✓`, `├`). |

Além disso, alguns scripts (`1.5`, `5`, `5.1`, `5.4`, `9`, `10`) chamam `sys.stdout.reconfigure(encoding='utf-8')` internamente para compatibilidade em execução direta via terminal.

---

## 3. Mecanismo `--config <json>` e Precedência

A comunicação entre a interface Streamlit e os scripts do pipeline ocorre por passagem de arquivo JSON via linha de comando, gerenciada por `run_script()` em [src/runner.py](../src/runner.py):

1. A aba correspondente em `src/tabs/` monta um dicionário Python `config` combinando os parâmetros globais de `st.session_state` e os campos específicos da aba.
2. `run_script()` serializa esse dicionário em um arquivo `.json` temporário (`tempfile.NamedTemporaryFile(..., suffix='.json', encoding='utf-8')`).
3. O subprocesso é iniciado com o mesmo interpretador Python do ambiente ativo:
   ```text
   [sys.executable, script_path, "--config", config_file]
   ```
4. Ao término do subprocesso (com sucesso ou erro), o bloco `finally` de `run_script()` remove o arquivo JSON temporário.

### Cobertura e Precedência

- **22 dos 23 scripts** em `codigos_py/` aceitam `--config <json>` via `argparse.ArgumentParser().parse_known_args()`.
- **JSON inline:** os scripts `1.2`, `1.3`, `1.3.1`, `1.4`, `1.5`, `7.1` e `7.2` verificam `os.path.isfile(_args.config)` e, caso não seja um arquivo em disco, fazem fallback para `json.loads(_args.config)`, aceitando também uma string JSON diretamente na linha de comando.
- **Exceção:** [codigos_py/3_desvios_nao-utilizar.py](../codigos_py/3_desvios_nao-utilizar.py) está **descontinuado**, não aceita `--config` e não é exposto na interface Streamlit.
- **Regra de precedência:**
  1. Valor presente no JSON passado via `--config` (maior prioridade).
  2. Valor padrão (*hardcoded*) no topo do script Python, usado quando a chave não é informada ou quando o script é executado diretamente sem `--config`.

> **Observação:** Os valores padrão exibidos na interface Streamlit (`src/tabs/`) podem diferir dos defaults *hardcoded* no topo de cada script (que refletem o último estudo executado manualmente). Quando o script é disparado pela UI, o valor da UI sempre prevalece.

---

## 4. Parâmetros Globais da Interface (`src/app.py`)

Definidos na barra lateral de [src/app.py](../src/app.py) e compartilhados entre todas as abas por meio de `st.session_state`:

| Parâmetro | Tipo | Valor Padrão na UI | Opções / Formato | Componentes Consumidores |
|---|---|---|---|---|
| `BASE_DADOS` | `str` (caminho) | `"C:/R_SMTR/dados"` | Caminho raiz dos dados e insumos | Abas `1` (`1`, `1.1`, `1.2`, `1.5`), `2`, `4`, `5` (`5`, `5.1`), `6`, `7` (`7`), `8` (`8`, `8.1`), `9`, `10` |
| `ano_gtfs` | `str` | `"2026"` | `YYYY` | Todas as abas (exceto modos `7.1` e `7.2`; nos modos `5.2`, `5.3` e `5.4` usado apenas para montar caminhos padrão na UI, não enviado no `--config`) |
| `mes_gtfs` | `str` | `"08"` | `MM` (dois dígitos) | Abas `1`, `2`, `4`, `5` (`5`, `5.1`), `6`, `8` (`8`), `9`, `10` |
| `estudo_gtfs` | `str` | `"02"` | `NN` (número do estudo, usado no sufixo `{NN}Q`) | Abas `1`, `2`, `4`, `5` (`5`, `5.1`), `6`, `8` (`8`), `9`, `10` |
| `gtfs_processar` | `str` | `"sppo"` | `"sppo"`, `"brt"`, `"rio"` | Abas `2`, `5` (`5`, `5.1`) |

### Derivação de `BASE_RESULTADOS`

As abas que gravam produtos analíticos (`tab_1_extrair_qh.py`, `tab_7_partidas.py`, `tab_8_extensoes.py`) derivam o valor padrão de `BASE_RESULTADOS` automaticamente a partir de `BASE_DADOS`:

```python
BASE_RESULTADOS = BASE_DADOS.replace("dados", "resultados")
```

Com o padrão `BASE_DADOS = "C:/R_SMTR/dados"`, `BASE_RESULTADOS` assume `"C:/R_SMTR/resultados"`. O valor pode ser sobrescrito individualmente no campo da aba ou no JSON de `--config`.

---

## 5. Estrutura de Diretórios de Entrada, Saída e Insumos

O pipeline espera a seguinte organização de diretórios fora do repositório (controlada por `BASE_DADOS` e `BASE_RESULTADOS`):

```text
<BASE_DADOS>/                              # Padrão: C:/R_SMTR/dados
├── calendario.json                        # Lista de feriados (chave "holidays", YYYY-MM-DD) — Script 2
├── gtfs/
│   └── <ano_gtfs>/                        # GTFS brutos, *_PROC.zip, *_FILTRADO.zip, *_COMBINADO.zip,
│                                          # gtfs_combi_*.zip, gtfs_rio-de-janeiro_pub.zip, *_com_qh.zip
├── viagens/
│   ├── sppo/<ano_velocidade>/<mes_velocidade>/        # Arquivos *.parquet (GPS SPPO) — Script 2
│   ├── rio/<ano_velocidade>/<mes_velocidade>/         # Arquivos *.parquet (GPS Rio) — Script 2
│   ├── brt/<ano_velocidade>/<mes_velocidade>/validas/ # Arquivos *.csv (GPS BRT) — Script 2
│   └── frescao/<ano_velocidade>/<mes_velocidade>/validas/ # Arquivos *.csv (GPS Frescão) — Script 2
├── shapes/
│   └── <ano_gtfs>/                        # Saída GIS: shapes_trajetos_*.{shp,gpkg} e shapes_pontos_*.{shp,gpkg} — Script 6
├── os/                                    # Saída de trajetos alternativos: os_*_excep*.csv — Script 4
└── insumos/
    ├── gtfs_cores.csv                     # Paleta de cores por route_short_name — Scripts 5, 5.1
    ├── trip_id_fantasma.txt               # Lista de trip_ids a remover (sem cabeçalho) — Scripts 5, 5.1, 7
    ├── gtfs_combi/                        # Arquivos .txt de substituição p/ GTFS combi (ou .../RIO/<ETAPA>/) — Scripts 5, 5.1
    └── gtfs_pub/                          # Arquivos .txt de substituição p/ GTFS pub (ou .../RIO/<ETAPA>/) — Scripts 5, 5.1

<RAIZ_DO_REPOSITORIO>/                     # Caminho relativo ao diretório de execução (cwd)
└── insumos_desvios/
    ├── descricao_desvios.csv              # Opcional no Script 6 (descrição textual de desvios); usado no Script 3 (descontinuado)
    └── linhas_desvios.csv                 # Usado apenas no Script 3 (descontinuado)

<BASE_RESULTADOS>/                         # Padrão: C:/R_SMTR/resultados
├── quadro_horario_extraido/
│   └── <ano_gtfs>/<mes_gtfs>/
│       ├── qh_por_linha/<estudo>Q/            # Saída do Script 1; entrada padrão do Script 1.2
│       ├── qh_partidas_por_linha/<estudo>Q/   # Saída do Script 1.1
│       ├── qh_por_linha_combinado/<estudo>Q/  # Saída do Script 1.2
│       ├── qh_por_linha_partidas/<estudo>Q/   # Saída do Script 1.3; conferida pelo 1.3.1; entrada padrão do 1.5
│       └── qh_por_linha_pf_gtfs/<estudo>Q/    # Saída do Script 1.4
├── partidas/                              # Saída do Script 7: partidas_{tipo_dia}.csv, partidas_{sufixo}.{csv,parquet}
├── extensoes/                             # Saída dos Scripts 8 e 8.1: extensoes_*.csv
└── lista_filtro/                          # Entrada padrão de arquivo do Script 9 (quando LISTA_FILTRO_RAW não é enviado)
```

Para detalhes de formato, colunas e convenções de nomenclatura de cada arquivo, consulte [data_dictionary.md](./data_dictionary.md).

---

## 6. Parâmetros de Execução por Etapa / Script

Nas tabelas abaixo, **Obrigatório** indica se o parâmetro precisa estar válido para a execução concluir sem erro (mesmo possuindo valor padrão no script ou na UI). Parâmetros globais (`BASE_DADOS`, `BASE_RESULTADOS`, `ano_gtfs`, `mes_gtfs`, `estudo_gtfs`) seguem os padrões descritos na [Seção 4](#4-parâmetros-globais-da-interface-srcapppy), salvo onde indicado.

### Etapa 1 — Quadros de Horários (Scripts 1 a 1.5)

Interface: [src/tabs/tab_1_extrair_qh.py](../src/tabs/tab_1_extrair_qh.py) (modos `1`, `1.1`, `1.2`, `1.3`, `1.3.1`, `1.4`, `1.5`).

#### Script `1` ([codigos_py/1_extrair_qh_especificado_no_gtfs.py](../codigos_py/1_extrair_qh_especificado_no_gtfs.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `end_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{ano}-{mes}-{estudo}Q.zip` | Mesmo padrão com globais da UI | Caminho do GTFS ZIP de entrada. |
| `linhas_rodar` | Sim | `["557"]` | `"371, 624, SN624, SV624"` | Lista (ou string separada por vírgula) de `trip_short_name` a extrair. |
| `services_to_run` | Sim | `["U_REG", "S_REG", "D_REG", "F_REG"]` | `["U_REG", "S_REG", "D_REG"]` | Lista de `service_id` alvo. |

#### Script `1.1` ([codigos_py/1.1_extrair_qh_partidas.py](../codigos_py/1.1_extrair_qh_partidas.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `end_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{ano}-{mes}-{estudo}Q.zip` | Mesmo padrão com globais da UI | Caminho do GTFS ZIP de entrada. |
| `linhas_rodar` | Não | Lista de 23 linhas (`804`...`SN893`) | Mesma lista de 23 linhas | Lista ou string separada por vírgula; vazio ou `"todas"` processa todas as linhas. |
| `services_to_run` | Sim | `["U_REG", "S_REG", "D_REG"]` | `["U_REG", "S_REG", "D_REG"]` | Lista ou string de `service_id` alvo. |
| `pasta_saida` | Não | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_partidas_por_linha/{estudo}Q` | Mesmo padrão | Diretório de gravação dos CSVs de partidas detalhadas. |

#### Script `1.2` ([codigos_py/1.2_combinar_quadros_horarios.py](../codigos_py/1.2_combinar_quadros_horarios.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `pasta_entrada` | Não | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_por_linha/{estudo}Q` | Mesmo padrão | Pasta contendo os CSVs extraídos pelo Script 1. |
| `pasta_saida` | Não | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_combinado/{estudo}Q` | Mesmo padrão | Pasta de saída dos CSVs combinados. |
| `servico_origem` | Sim | `"S_REG"` | `"U_REG"` | `service_id` do qual será importada a janela horária. |
| `servico_destino` | Sim | `"D_REG"` | `"D_REG"` | `service_id` base que receberá o recorte da origem. |
| `hora_inicio` | Sim | `"09:00:00"` | `"06:00:00"` | Início da janela a importar (`HH:MM:SS`, inclusivo). |
| `hora_fim` | Sim | `"18:00:00"` | `"21:00:00"` | Fim da janela a importar (`HH:MM:SS`, exclusivo). |
| `linhas_rodar` | Não | Lista de 23 linhas (`804`...`SN893`) | `""` (todas as linhas) | Lista ou string separada por vírgula; vazio ou `"todas"` processa todas as linhas encontradas. |

#### Script `1.3` ([codigos_py/1.3_qh_a_partir_de_partidas.py](../codigos_py/1.3_qh_a_partir_de_partidas.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `caminho_partidas` | Sim | `"Simulações - Página23.csv"` | `"partidas_pf_sppo_como_du.csv"` | Caminho do CSV de contagens (formato *wide* ou longo). |
| `service_id` | Sim | `"F_REG"` | `"F_REG"` | Calendário gravado no nome dos CSVs e no Excel. |
| `granularidade_headway` | Não | `300` | `300` | Múltiplo em segundos para arredondamento para baixo do headway. |
| `traco_ausente` | Não | `"zerar"` | `"zerar"` | Tratamento de `"-"` / não numéricos: `"zerar"` ou `"erro"`. |
| `linhas_rodar` | Não | `[]` (todas) | `""` (todas) | Filtro opcional de serviços (`trip_short_name`). |
| `pasta_saida` | Não | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_partidas/{estudo}Q` | Mesmo padrão | Pasta de gravação dos CSVs, Excel e relatórios. |
| `gerar_relatorio` | Não | `True` | `True` | Grava `relatorio_bandas.csv` e `_resumo.txt`. |
| `gerar_excel` | Não | `True` | `True` | Gera workbook Excel com uma aba por serviço. |
| `nome_excel` | Não | `quadros_partidas_{service_id}.xlsx` | `""` (usa padrão do script) | Nome do arquivo `.xlsx` dentro de `pasta_saida`. |
| `tipo_dia` | Não | Mesmo valor de `service_id` | `""` (usa `service_id`) | Rótulo textual exibido no cabeçalho das abas do Excel. |

#### Script `1.3.1` ([codigos_py/1.3.1_conferir_partidas_geradas.py](../codigos_py/1.3.1_conferir_partidas_geradas.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `caminho_partidas` | Sim | `"partidas_pf_sppo_como_du.csv"` | `"partidas_pf_sppo_como_du.csv"` | Tabela de contagens original usada na geração (Script 1.3). |
| `pasta_saida` | Não | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_partidas/{estudo}Q` | Mesmo padrão | Pasta conferida onde estão os `horarios_*.csv` e onde serão gravados os relatórios de conferência. |
| `service_id` | Sim | `"F_REG"` | `"F_REG"` | Calendário esperado nos nomes dos arquivos. |
| `traco_ausente` | Não | `"zerar"` | `"zerar"` | Deve coincidir com o valor usado no Script 1.3 (`"zerar"` ou `"erro"`). |
| `linhas_rodar` | Não | `[]` (todas) | `""` (todas) | Deve refletir o mesmo filtro de linhas usado na geração. |
| `verificar_excel` | Não | `True` | `True` | Se `True`, audita também as partidas do workbook Excel contra os CSVs. |
| `nome_excel` | Não | `quadros_partidas_{service_id}.xlsx` | `""` (usa padrão do script) | Nome do arquivo `.xlsx` conferido em `pasta_saida`. |

#### Script `1.4` ([codigos_py/1.4_qh_pf_a_partir_do_gtfs.py](../codigos_py/1.4_qh_pf_a_partir_do_gtfs.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `end_gtfs` | Sim | `<raiz_repo>/0171_gtfs_out_26_1E_ret.zip` | Mesmo padrão | Caminho do GTFS ZIP de entrada. |
| `service_id` | Sim | `"F_REG"` | `"F_REG"` | Calendário de destino gravado nos arquivos gerados. |
| `agencias_excluidas` | Não | `["20001"]` | `"20001"` | `agency_id` excluídos integralmente (MOBI-Rio). |
| `route_types_permitidos` | Não | `["700"]` | `"700"` | `route_type` incluídos (ônibus convencional). |
| `mapa_base` | Não | Ver [Seção 7](#7-constantes-técnicas-relevantes) | Não exposto na UI (usa padrão do script) | Dicionário `{agency_id: service_id_origem}` para seleção da base DU ou Sábado. |
| `linhas_rodar` | Não | `[]` (todas) | `""` (todas) | Filtro opcional de linhas. |
| `pasta_saida` | Não | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_pf_gtfs/{estudo}Q` | Mesmo padrão | Pasta de saída dedicada (separada do Script 1.3). |
| `gerar_relatorio` | Não | `True` | `True` | Grava `relatorio_bandas.csv` e `_resumo.txt`. |
| `gerar_excel` | Não | `True` | `True` | Gera workbook Excel com uma aba por serviço. |
| `nome_excel` | Não | `quadros_partidas_{service_id}.xlsx` | `""` (usa padrão do script) | Nome do arquivo `.xlsx`. |
| `tipo_dia` | Não | Mesmo valor de `service_id` | `""` (usa `service_id`) | Rótulo de tipo de dia no Excel. |

#### Script `1.5` ([codigos_py/1.5_carregar_qh_no_gtfs.py](../codigos_py/1.5_carregar_qh_no_gtfs.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs_base` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{sufixo}_completo.zip` | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{sufixo}.zip` | GTFS ZIP base a ser modificado. |
| `caminho_saida` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{sufixo}_com_qh.zip` | Mesmo padrão | Caminho do novo GTFS ZIP gerado. |
| `arquivos_qh` | Sim | `C:/R_SMTR/resultados/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_partidas/{estudo}Q` | `{BASE_RESULTADOS}/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_partidas/{estudo}Q` | Pasta contendo CSVs de QH, caminho de um CSV ou lista separada por vírgula. |
| `service_id_fallback` | Não | `"F_REG"` | `"F_REG"` | Calendário usado quando o nome do arquivo CSV não termina em um `service_id` conhecido. |
| `permitir_clonagem` | Não | `False` | `False` | Se `True`, permite clonar viagens molde de `U_REG` quando a linha ainda não possui o calendário alvo no GTFS. |

---

### Etapa 2 — Ajustar Stop Times (Script 2)

Script: [codigos_py/2_ajustar_stop_times.py](../codigos_py/2_ajustar_stop_times.py) · Interface: [src/tabs/tab_2_ajustar_st.py](../src/tabs/tab_2_ajustar_st.py).

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `gtfs_processar` | Sim | `"sppo"` | Valor global (`"sppo"`) | Modal processado (`"sppo"`, `"brt"` ou `"rio"`). Define formato e subpasta das viagens GPS. |
| `endereco_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/{gtfs_processar}_{ano}-{mes}-{estudo}Q.zip` | Mesmo padrão | GTFS ZIP bruto de entrada. A saída é gravada como `*_PROC.zip` na mesma pasta de `gtfs/{ano}/`. |
| `velocidade_padrao_kmh` | Não | `15.0` | `15.0` | Velocidade fallback (km/h) para correção de horários faltantes sem histórico GPS. |
| `ano_velocidade` | Sim | `"2025"` | `"2025"` | Ano da base de viagens GPS em `viagens/{modal}/{ano}/{mes}/`. |
| `mes_velocidade` | Sim | `"10"` | `"10"` | Mês da base de viagens GPS em `viagens/{modal}/{ano}/{mes}/`. |

---

### Etapa 4 — Trajetos Alternativos (Script 4)

Script: [codigos_py/4_trajetos_alternativos.py](../codigos_py/4_trajetos_alternativos.py) · Interface: [src/tabs/tab_4_trajetos.py](../src/tabs/tab_4_trajetos.py).

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_{ano}-{mes}-{estudo}Q_PROC.zip` | Mesmo padrão | GTFS ZIP de entrada (normalmente o `*_PROC.zip` gerado na Etapa 2). |
| `caminho_saida` | Sim | `{BASE_DADOS}/os/os_{ano}-{mes}-{estudo}_excep_sppo.csv` | `{BASE_DADOS}/os/os_{ano}-{mes}-{estudo}_excep.csv` | Caminho do CSV de relatório de trajetos alternativos (OS). |
| `CALENDARIOS_ALVO` | Não | `["EXCEP"]` | `["EXCEP"]` | Lista de `service_id` a filtrar; se vazio, considera todos os calendários. |

---

### Etapa 5 — Junção e Deduplicação de GTFS (Scripts 5 a 5.4)

Interface: [src/tabs/tab_5_juntar.py](../src/tabs/tab_5_juntar.py).

#### Script `5` ([codigos_py/5_juntar_gtfs.py](../codigos_py/5_juntar_gtfs.py)) — Juntar SPPO + BRT

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `gtfs_processar` | Sim | `"sppo"` | Valor global (`"sppo"`) | `"sppo"` ou `"rio"`; define o caminho das pastas de substituição (`insumos/gtfs_combi/` e `insumos/gtfs_pub/`). |
| `etapa_gtfs_rio` | Condicional | `"ETAPA_01"` | `"ETAPA_01"` | Etapa(s) do GTFS Rio separadas por vírgula (ex.: `"ETAPA_01,ETAPA_02"`), usadas quando `gtfs_processar != "sppo"`. |
| `endereco_sppo` | Sim | `{BASE_DADOS}/gtfs/{ano}/{gtfs_processar}_{sufixo}_PROC.zip` | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_PROC.zip` | GTFS SPPO (ou Rio) processado. |
| `endereco_brt` | Sim | `{BASE_DADOS}/gtfs/{ano}/brt_{sufixo}_PROC.zip` | Mesmo padrão | GTFS BRT processado. |
| `endereco_gtfs_combi` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{sufixo}.zip` | Mesmo padrão | Caminho de saída do GTFS combinado (além do público `gtfs_rio-de-janeiro_pub.zip`). |
| `linhas_excluir` | Não | `[]` | `""` (`[]`) | Lista de `trip_short_name` a remover antes da junção. |

#### Script `5.1` ([codigos_py/5.1_juntar_gtfs_sppo.py](../codigos_py/5.1_juntar_gtfs_sppo.py)) — Juntar Único (SPPO, BRT ou Rio)

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `gtfs_processar` | Sim | `"rio"` | `"rio"` (`["rio", "brt", "sppo"]`) | Modal único a processar. |
| `etapa_gtfs_rio` | Condicional | `"ETAPA_01"` | `"ETAPA_01"` | Etapa(s) do GTFS Rio (separadas por vírgula; ordem define prioridade). |
| `endereco_sppo` | Condicional | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_PROC.zip` | Mesmo padrão | Usado apenas quando `gtfs_processar == "sppo"` (para `"rio"`, o script lê diretamente `rio_{sufixo}_PROC.zip`). |
| `endereco_brt` | Condicional | `{BASE_DADOS}/gtfs/{ano}/brt_{sufixo}_PROC.zip` | Mesmo padrão | Usado quando `gtfs_processar == "brt"`. |
| `endereco_gtfs_combi` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{sufixo}.zip` | Mesmo padrão | Caminho de saída do GTFS combinado. |

#### Script `5.2` ([codigos_py/5.2_juntar_gtfs_simples.py](../codigos_py/5.2_juntar_gtfs_simples.py)) — Concatenar Simples

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `INPUT_ZIPS` | Sim | Lista com 2 caminhos em `gtfs/2027/` | 2 caminhos em `gtfs/{ano}/` (ou uploads ZIP temporários) | Lista de caminhos dos arquivos GTFS ZIP a concatenar. |
| `OUTPUT_ZIP` | Sim | `C:/R_SMTR/dados/gtfs/2026/gtfs_combined.zip` | `{BASE_DADOS}/gtfs/{ano}/gtfs_combined.zip` | Caminho do GTFS ZIP de saída. |

#### Script `5.3` ([codigos_py/5.3_juntar_gtfs_substituicao.py](../codigos_py/5.3_juntar_gtfs_substituicao.py)) — Juntar com Substituição

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `GTFS_1_PATH` | Sim | `C:/R_SMTR/dados/gtfs/2030/gtfs_combined_combi.zip` | `{BASE_DADOS}/gtfs/{ano}/0143_gtfs_ago_26_1E_ret1.zip` | GTFS base cujas rotas sobrepostas serão substituídas. |
| `GTFS_2_PATH` | Sim | `C:/R_SMTR/dados/gtfs/2030/GTFS_Filtrado.zip` | `{BASE_DADOS}/gtfs/{ano}/GTFS_Filtrado_141.zip` | GTFS modificador que substitui as rotas equivalentes no GTFS 1. |
| `OUTPUT_ZIP` | Sim | `C:/R_SMTR/dados/gtfs/2030/gtfs_combined_combi2.zip` | `{BASE_DADOS}/gtfs/{ano}/gtfs_combined2.zip` | Caminho do GTFS ZIP resultante. |

#### Script `5.4` ([codigos_py/5.4_eliminar_duplicatas_gtfs.py](../codigos_py/5.4_eliminar_duplicatas_gtfs.py)) — Eliminar Duplicatas

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs` | Sim | `C:/R_SMTR/dados/GTFS/2029/0164_gtfs_out_26_1E.zip` | `{BASE_DADOS}/gtfs/{ano}/gtfs_combi_{sufixo}.zip` | Caminho do GTFS ZIP a deduplicar (adiciona `.zip` se omitido). |
| `caminho_saida` | Não | `""` (sobrescreve `endereco_gtfs`) | `""` (sobrescreve entrada) | Caminho alternativo de saída; vazio sobrescreve o arquivo de entrada. |
| `arquivos_alvo` | Não | `[endereco_gtfs]` | Não exposto na UI | Lista opcional de múltiplos ZIPs para deduplicação em lote via CLI. |

---

### Etapa 6 — Gerar Shapes GIS (Script 6)

Script: [codigos_py/6_gerar_shapes.py](../codigos_py/6_gerar_shapes.py) · Interface: [src/tabs/tab_6_shapes.py](../src/tabs/tab_6_shapes.py).

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs_combi` | Sim | `{BASE_DADOS}/gtfs/{ano}/gtfs_rio-de-janeiro_pub_completo.zip` | `{BASE_DADOS}/gtfs/{ano}/gtfs_rio-de-janeiro_pub.zip` | GTFS ZIP de entrada (geralmente o GTFS público final). |
| `pasta_shape_sppo` | Sim | `{BASE_DADOS}/shapes/{ano}` | `{BASE_DADOS}/shapes/{ano}` | Diretório de saída dos arquivos `.shp` e `.gpkg`. |

---

### Etapa 7 — Lista e Combinação de Partidas (Scripts 7 a 7.2)

Interface: [src/tabs/tab_7_partidas.py](../src/tabs/tab_7_partidas.py) (modos `7`, `7.1`, `7.2`).

#### Script `7` ([codigos_py/7_lista_partidas.py](../codigos_py/7_lista_partidas.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_2028-11-05Q_PROC.zip` | `{BASE_DADOS}/gtfs/2026/gtfs_combi_2026-10-02Q_RIO.zip` | GTFS ZIP de entrada. |
| `tipos_dia` | Sim | `["du", "sab", "dom", "pf"]` | `["du", "sab", "dom", "pf"]` | Tipos de dia a processar: `du` (`U`), `sab` (`S`), `dom` (`D`), `pf` (`F` / `F_REG`). |
| `linhas_excluir` | Não | `[]` | `""` (`[]`) | Lista de `trip_short_name` a excluir (aceita vírgula ou quebra de linha na UI). |

#### Script `7.1` ([codigos_py/7.1_resumo_os_domingo_du.py](../codigos_py/7.1_resumo_os_domingo_du.py))

| Parâmetro | Obrigatório | Padrão (Script e UI) | Descrição |
|---|---|---|---|
| `caminho_entrada` | Sim | `C:\R_SMTR\resultados\OS_historico\2026_SET_1ºESTUDO_RETIFICAÇÃO\partidas\partidas_2026-09-01Q.parquet` | Arquivo de partidas consolidado gerado pelo Script 7 (`.parquet` ou `.csv`). |
| `pasta_saida` | Sim | `C:\R_SMTR\resultados\OS_historico\2026_SET_1ºESTUDO_RETIFICAÇÃO\arquivos_os` | Diretório de gravação dos resumos `.xlsx` e `.csv`. |
| `nome_base_saida` | Não | `"tabela_domingo_ajustada"` | Prefixo dos arquivos `<nome>.xlsx` e `<nome>.csv`. |
| `hora_inicio` | Não | `"06:00:00"` | Início da janela de dia útil importada (`HH:MM:SS`, inclusivo). |
| `hora_fim` | Não | `"20:00:00"` | Fim da janela de dia útil importada (`HH:MM:SS`, exclusivo). |

#### Script `7.2` ([codigos_py/7.2_combinador_partidas.py](../codigos_py/7.2_combinador_partidas.py))

| Parâmetro | Obrigatório | Padrão (Script e UI) | Descrição |
|---|---|---|---|
| `caminho_du` | Sim | `"quadros_du.csv"` | CSV de partidas de dia útil. |
| `caminho_dom` | Sim | `"quadros_dom.csv"` | CSV de partidas de domingo. |
| `caminho_saida` | Sim | `"quadros_dom_04-10.csv"` | CSV combinado de saída (janela fixa `06:00:00`–`20:00:00` de DU). |

---

### Etapa 8 — Gerar Extensões (Scripts 8 e 8.1)

Interface: [src/tabs/tab_8_extensoes.py](../src/tabs/tab_8_extensoes.py).

#### Script `8` ([codigos_py/8_gerar_extensoes.py](../codigos_py/8_gerar_extensoes.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/0173_gtfs_out_26_2E.zip` | `{BASE_DADOS}/gtfs/{ano}/gtfs_rio-de-janeiro_pub.zip` | GTFS ZIP de entrada. |
| `BASE_RESULTADOS` | Sim | `"C:/R_SMTR/resultados"` | Derivado de `BASE_DADOS` | Grava em `{BASE_RESULTADOS}/extensoes/extensoes_{ano}-{mes}-{estudo}Q.csv`. |

#### Script `8.1` ([codigos_py/8.1_gerar_extensoes_rio.py](../codigos_py/8.1_gerar_extensoes_rio.py))

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `sufixo` | Sim | `f"rio_{ano_gtfs}-05"` | `f"rio_{ano}-05"` | Sufixo no formato `rio_YYYY-MM` usado para localizar o ZIP e nomear a saída. |
| `endereco_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/{sufixo}.zip` | Mesmo padrão | GTFS ZIP de entrada no formato Rio. |
| `BASE_RESULTADOS` | Sim | `"C:/R_SMTR/resultados"` | Derivado de `BASE_DADOS` | Grava em `{BASE_RESULTADOS}/extensoes/extensoes_{sufixo}.csv`. |

---

### Etapa 9 — Filtrar GTFS por Lista (Script 9)

Script: [codigos_py/9_filtrar_gtfs_por_lista.py](../codigos_py/9_filtrar_gtfs_por_lista.py) · Interface: [src/tabs/tab_9_filtrar.py](../src/tabs/tab_9_filtrar.py).

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `endereco_gtfs` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_PROC.zip` | Mesmo padrão (`mes="12"`, `estudo="08"` na aba) | GTFS ZIP de entrada. |
| `caminho_saida` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_FILTRADO.zip` | Mesmo padrão | GTFS ZIP filtrado de saída. |
| `CALENDARIOS_ALVO` | Não | `["EXCEP"]` | `["EXCEP"]` | Lista de `service_id` filtrados; vazio usa todos. |
| `LISTA_FILTRO_RAW` | Condicional | `None` (lê `LISTA_FILTRO_PATH`) | Texto colado ou upload CSV/TSV | Conteúdo textual da lista de filtro (separador `,` ou `\t` detectado automaticamente). |
| `LISTA_FILTRO_PATH` | Condicional | `"C:/R_SMTR/resultados/lista_filtro/alternativos_155_faltam.csv"` | Não enviado (UI usa `LISTA_FILTRO_RAW`) | Caminho de arquivo CSV/TSV usado apenas quando `LISTA_FILTRO_RAW` não é fornecido. |

---

### Etapa 10 — Juntar Dois GTFS com Prioridade (Script 10)

Script: [codigos_py/10_juntar_dois_gtfs.py](../codigos_py/10_juntar_dois_gtfs.py) · Interface: [src/tabs/tab_10_juntar_dois.py](../src/tabs/tab_10_juntar_dois.py).

| Parâmetro | Obrigatório | Padrão (Script) | Padrão (UI) | Descrição |
|---|---|---|---|---|
| `GTFS_PRINCIPAL` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_FILTRADO.zip` | Mesmo padrão (`mes="12"`, `estudo="08"` na aba) | GTFS com **prioridade** na resolução de chaves duplicadas. |
| `GTFS_SECUNDARIO` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_PROC.zip` | Mesmo padrão | GTFS complementar. |
| `GTFS_SAIDA` | Sim | `{BASE_DADOS}/gtfs/{ano}/sppo_{sufixo}_COMBINADO.zip` | Mesmo padrão | Caminho do GTFS ZIP combinado final. |

---

## 7. Constantes Técnicas Relevantes

| Constante / Regra | Valor(es) | Onde é Definida | Uso no Pipeline |
|---|---|---|---|
| **Projeção Geográfica (WGS84)** | `EPSG:4326` | `4`, `6`, `7`, `8`, `8.1` | CRS de entrada das coordenadas `shape_pt_lon`/`shape_pt_lat` e `stop_lon`/`stop_lat`, e CRS das camadas exportadas em `6_gerar_shapes.py`. |
| **Projeção Métrica (SIRGAS 2000 / UTM 23S)** | `EPSG:31983` | `4`, `6`, `7`, `8`, `8.1` | CRS de reprojeção para cálculo de comprimento (`geometry.length`) dos trajetos em metros. |
| **`SERVICE_IDS_CONHECIDOS`** | `{"U_REG", "S_REG", "D_REG", "F_REG", "U", "S", "D", "F", "EXCEP", "DESAT"}` | [src/gtfs_carregar_qh.py](../src/gtfs_carregar_qh.py) | Detecção automática do `service_id` a partir do sufixo do nome dos CSVs de QH no Script `1.5` e no `app_carregar_qh.py`. |
| **`mapa_base` (Script 1.4)** | `"22002": "U_REG"` (Intersul), `"22003": "U_REG"` (Internorte), `"22004": "U_REG"` (Transcarioca), `"22005": "U_REG"` (Santa Cruz), `"A2": "S_REG"` (GTU), `"B2": "S_REG"` (TUSE) | [codigos_py/1.4_qh_pf_a_partir_do_gtfs.py](../codigos_py/1.4_qh_pf_a_partir_do_gtfs.py) | Define qual `service_id` do GTFS serve de base para gerar o quadro de ponto facultativo (`F_REG`) de cada agência. |
| **`agencias_excluidas`** | `["20001"]` (MOBI-Rio) | [codigos_py/1.4_qh_pf_a_partir_do_gtfs.py](../codigos_py/1.4_qh_pf_a_partir_do_gtfs.py) | Exclui integralmente a agência MOBI-Rio na geração de QH de ponto facultativo. |
| **`route_types_permitidos`** | `["700"]` | [codigos_py/1.4_qh_pf_a_partir_do_gtfs.py](../codigos_py/1.4_qh_pf_a_partir_do_gtfs.py) | Restringe o Script `1.4` a linhas de ônibus convencional. |
| **`FAIXAS_PADRAO` (14 faixas)** | `00:00-01:00`, `01:00-02:00`, `02:00-03:00`, `03:00-04:00`, `04:00-05:00`, `05:00-06:00`, `06:00-09:00`, `09:00-12:00`, `12:00-15:00`, `15:00-18:00`, `18:00-21:00`, `21:00-22:00`, `22:00-23:00`, `23:00-24:00` | `1.3`, `1.3.1`, `7` (`get_faixa`) | Agrupamento padrão de partidas em 14 faixas horárias (1h na madrugada/noite; blocos de 3h entre 06:00 e 21:00). |
| **`FAIXAS_RESUMO` (20 faixas)** | `00:00-00:59` até `05:00-05:59`, `06:00-08:59`, `09:00-11:59`, `12:00-14:59`, `15:00-17:59`, `18:00-20:59`, `21:00-21:59` até `29:00-29:59` | [src/qh_format.py](../src/qh_format.py) | Faixas de resumo usadas no comparador standalone [src/app_format_qh.py](../src/app_format_qh.py), cobrindo virada de meia-noite até `29:59`. |
| **Ajustes fixos de tempo de viagem (GPS)** | Serviço `851` (`direction_id == 0`): `+1800s` (+30 min); Serviço `SP485` (`direction_id == 0`): `+1200s` (+20 min); Demais serviços/sentidos: `+360s` (+6 min) | [codigos_py/2_ajustar_stop_times.py](../codigos_py/2_ajustar_stop_times.py) (`adjust_time`) | Acréscimo aplicado ao tempo de viagem observado por GPS antes da remoção de outliers (IQR 1,5x) e cálculo da velocidade média. |
| **Barra de progresso assintótica (`runner.py`)** | `_PROGRESS_CAP = 0.95`, `_PROGRESS_TAU = 90.0` s, `_POLL_TIMEOUT = 0.3` s | [src/runner.py](../src/runner.py) | Controla atualização da barra de progresso na interface Streamlit enquanto o subprocesso executa (atinge 100% apenas ao concluir com código `0`). |

### `CHAVES_PRIMARIAS` (Script `10_juntar_dois_gtfs.py`)

Usadas em [codigos_py/10_juntar_dois_gtfs.py](../codigos_py/10_juntar_dois_gtfs.py) para deduplicação com prioridade para `GTFS_PRINCIPAL`:

| Tabela GTFS | Chave Primária | Comportamento em Conflito |
|---|---|---|
| `agency` | `['agency_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `stops` | `['stop_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `routes` | `['route_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `trips` | `['trip_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `stop_times` | `['trip_id', 'stop_sequence']` | Mantém registro de `GTFS_PRINCIPAL` |
| `calendar` | `['service_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `calendar_dates` | `['service_id', 'date']` | Mantém registro de `GTFS_PRINCIPAL` |
| `shapes` | `['shape_id', 'shape_pt_sequence']` | Mantém registro de `GTFS_PRINCIPAL` |
| `frequencies` | `['trip_id', 'start_time']` | Mantém registro de `GTFS_PRINCIPAL` |
| `fare_attributes` | `['fare_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `fare_rules` | `['fare_id', 'route_id']` | Mantém registro de `GTFS_PRINCIPAL` |
| `feed_info` | `[]` (sem chave) | Mantém apenas o registro de `GTFS_PRINCIPAL` |

---

## Documentação Relacionada

- [README.md](../README.md) — Visão geral, instalação e execução rápida.
- [architecture.md](./architecture.md) — Arquitetura da aplicação e decisões de projeto.
- [pipeline.md](./pipeline.md) — Fluxo completo de execução e dependências entre etapas.
- [scripts_reference.md](./scripts_reference.md) — Catálogo técnico de todos os scripts e módulos.
- [data_dictionary.md](./data_dictionary.md) — Dicionário de dados, esquemas e ciclo de vida dos artefatos.
- [testing.md](./testing.md) — Testes automatizados e validações de consistência.
- [troubleshooting.md](./troubleshooting.md) — Diagnóstico e solução de problemas conhecidos.
