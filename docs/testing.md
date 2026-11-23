# Testes e Validações

Este documento descreve a suíte de testes automatizados, as verificações de consistência embutidas no pipeline e o fluxo de validação externa utilizado pelo projeto `processar_gtfs`.

## Índice

- [Ferramentas de teste](#ferramentas-de-teste)
- [Organização dos testes](#organização-dos-testes)
- [Comandos de execução](#comandos-de-execução)
- [Escopo de cobertura e lacunas conhecidas](#escopo-de-cobertura-e-lacunas-conhecidas)
- [Validações embutidas no pipeline](#validações-embutidas-no-pipeline)
- [Validação externa (`validacao_gtfs`)](#validação-externa-validacao_gtfs)

---

## Ferramentas de teste

O projeto utiliza exclusivamente o módulo `unittest` da biblioteca padrão do Python para testes automatizados. Não há dependência de frameworks externos de teste (como `pytest`) no arquivo [`requirements.txt`](../requirements.txt).

As dependências de dados (`pandas`, `numpy`, `openpyxl`) são utilizadas nos testes apenas para criar e validar estruturas GTFS sintéticas em memória ou em diretórios temporários.

---

## Organização dos testes

Os testes automatizados ficam centralizados no diretório [`tests/`](../tests/) e cobrem módulos de lógica pura em [`src/`](../src/) e a integração CLI do carregador de quadros de horários.

| Arquivo | Módulo / Script testado | Quantidade de testes | Tipo |
| --- | --- | --- | --- |
| [`tests/test_qh_format.py`](../tests/test_qh_format.py) | [`src/qh_format.py`](../src/qh_format.py) | 17 | Unitário |
| [`tests/test_gtfs_carregar_qh.py`](../tests/test_gtfs_carregar_qh.py) | [`src/gtfs_carregar_qh.py`](../src/gtfs_carregar_qh.py) e [`codigos_py/1.5_carregar_qh_no_gtfs.py`](../codigos_py/1.5_carregar_qh_no_gtfs.py) | 7 | Unitário + integração CLI |

### `tests/test_qh_format.py` (17 testes)

Usa um arquivo GTFS ZIP sintético gerado em memória (`_gtfs_zip()`) e organiza os casos em quatro classes:

- **`TestTempo`**: conversão de horários `HH:MM:SS` (incluindo horas >= 24h) para segundos (`horario_to_seconds`), conversão inversa (`seconds_to_horario`), desenrolamento de virada de meia-noite (`unwrap_midnight`) e parsing/validação de listas de partidas (`parse_partidas`).
- **`TestGtfs`**: leitura de GTFS ZIP em memória (`load_gtfs_zip`), montagem de opções de linhas (`route_choices`) e expansão de `frequencies.txt` em segundos de partida (`get_departure_seconds`), incluindo o cenário de tabela de frequências vazia.
- **`TestBandas`**: agrupamento de partidas em faixas de headway constante (`bands_from_departures`), tratamento de erro para lista com apenas uma partida e geração do DataFrame no formato de Quadro Horário do Script 1 (`qh_dataframe`, com `trip_id` vazio).
- **`TestComparacaoResumo`**: formatação da tabela de partidas (`schedule_display`), comparação entre programação GTFS e programação proposta (`comparison_table`, incluindo igualdade, setas direcionais e partidas sem par) e resumo por faixa horária (`summary_table`).

### `tests/test_gtfs_carregar_qh.py` (7 testes)

Usa um GTFS sintético completo em memória (`criar_gtfs_sintetico()`, contendo `routes`, `trips`, `stop_times`, `frequencies`, `calendar` e `stops`) e valida os seguintes cenários na classe `TestCarregarQH`:

- **`test_extrair_service_id_do_nome`**: extração do `service_id` a partir de nomes de arquivos CSV (`F_REG`, `U_REG`, `S_REG`, `F` e retorno `None` quando ausente).
- **`test_parse_qh_csv`**: parsing de CSV de quadro de horários (serviço, `headsign`, `service_id`, bandas e total de partidas).
- **`test_substituicao_direta_apenas_no_sentido`**: substituição direta em um único sentido (`Anchieta` em `U_REG`), validando a preservação intacta do sentido oposto (`Candelária`), o alinhamento do `departure_time` inicial em `stop_times.txt` ao `start_time` da banda e o **invariante 1:1** (`trip_id` estritamente único em `trips.txt` e `frequencies.txt`).
- **`test_clonagem_sem_permissao_lanca_erro`**: classificação como `REQUER_CLONAGEM` com molde `U_REG` quando o calendário alvo (`F_REG`) não existe no GTFS, e lançamento obrigatório de `PermissionError` quando `permitir_clonagem=False`.
- **`test_clonagem_com_permissao_sucesso`**: clonagem autorizada (`permitir_clonagem=True`), validando criação da nova trip, cópia das paradas em `stop_times.txt`, inserção das frequências e inclusão de `F_REG` em `calendar.txt`.
- **`test_write_and_read_gtfs_zip`**: round-trip de gravação e releitura de GTFS em ZIP (`write_gtfs` / `read_gtfs`).
- **`test_cli_integration`**: execução real via `subprocess.run` de [`codigos_py/1.5_carregar_qh_no_gtfs.py`](../codigos_py/1.5_carregar_qh_no_gtfs.py) com `--config`, combinando substituição direta e clonagem em diretório temporário e verificando a unicidade de `trip_id` no ZIP resultante.

---

## Comandos de execução

Execute os comandos a partir da raiz do repositório, com o ambiente virtual `.venv` ativado.

### Suíte completa

```powershell
python -m unittest discover -s tests -t . -v
```

### Módulos individuais

```powershell
# Testes da formatação e análise de quadros de horários (17 testes)
python -m unittest tests.test_qh_format -v

# Testes do carregador de quadros de horários e integração CLI 1.5 (7 testes)
python -m unittest tests.test_gtfs_carregar_qh -v
```

---

## Escopo de cobertura e lacunas conhecidas

Atualmente, a cobertura automatizada com `unittest` concentra-se nos módulos puros em `src/` (`src/qh_format.py` e `src/gtfs_carregar_qh.py`) e na integração CLI de `codigos_py/1.5_carregar_qh_no_gtfs.py`.

Lacunas conhecidas de cobertura automatizada:

- **Demais scripts de `codigos_py/`** (`1`, `1.1`, `1.2`, `1.3`, `1.3.1`, `1.4`, `2`, `4`, `5*`, `6`, `7*`, `8*`, `9`, `10`): não possuem suíte unitária em `tests/`. A verificação de consistência depende dos gates internos de execução, dos relatórios gerados em disco e da bateria de validação externa.
- **Interface Streamlit** (`src/app.py`, `src/tabs/*`, `src/runner.py`, `src/app_format_qh.py`, `src/app_carregar_qh.py`): não possui testes automatizados de interface.

---

## Validações embutidas no pipeline

Mesmo nos scripts sem cobertura em `tests/`, o pipeline implementa checagens rígidas para interromper execuções inconsistentes antes de propagar erros para etapas seguintes.

### Auditoria independente — `1.3.1_conferir_partidas_geradas.py`

O script [`codigos_py/1.3.1_conferir_partidas_geradas.py`](../codigos_py/1.3.1_conferir_partidas_geradas.py) realiza conferência independente sobre os artefatos produzidos por [`codigos_py/1.3_qh_a_partir_de_partidas.py`](../codigos_py/1.3_qh_a_partir_de_partidas.py). Ele relê diretamente a tabela de contagens de entrada e os arquivos `horarios_*.csv` gravados em disco (sem confiar no `_resumo.txt` ou no `relatorio_bandas.csv` da geração).

- **Reexpansão e comparação**: reexpande cada banda (`n = (end - start) / headway`) e compara a contagem resultante por `(servico, sentido, faixa)` com a entrada.
- **Verificação do Excel**: quando `verificar_excel=True`, confere também a contagem de partidas em cada bloco do arquivo `.xlsx` frente à expansão dos CSVs.
- **Classificação de anomalias**:
  - `FALTANDO`: quadro esperado pela entrada não encontrado em disco.
  - `SOBRANDO`: arquivo de quadro presente para grupo sem partidas na entrada.
  - `ORFAO`: arquivo `horarios_*.csv` presente na pasta que não corresponde a nenhum grupo esperado.
  - `BANDA`: banda com `headway < 1`, intervalo não divisível pelo headway, `start_time` fora da faixa ou `end_time` ultrapassando o fim da faixa.
  - `CELULA`: divergência entre contagem de entrada e contagem expandida em uma célula `(servico, sentido, faixa)`.
  - `EXCEL`: divergência entre o número de partidas nos blocos do `.xlsx` e a expansão dos CSVs.
- **Saídas e código de retorno**: gera `relatorio_conferencia_partidas.csv` e `_conferencia_resumo.txt` na pasta conferida. Retorna exit code `0` quando não há anomalias e `1` (`raise SystemExit(1)`) em caso de falha.

Execução via CLI:

```powershell
python codigos_py/1.3.1_conferir_partidas_geradas.py --config caminho/para/config.json
```

Também disponível na **aba 1 → modo 1.3.1** de `src/app.py`.

### Gates internos de preservação em `1.3` e `1.4`

- **[`codigos_py/1.3_qh_a_partir_de_partidas.py`](../codigos_py/1.3_qh_a_partir_de_partidas.py)**: antes de gravar os CSVs, compara entrada × saída por `(servico, sentido, faixa)`, verifica vazamento de bandas fora da faixa, `headway >= 1`, `end > start`, aderência à granularidade e igualdade do total de partidas. Se o gate falhar (ou se o total expandido no Excel divergir da saída), aborta com `SystemExit(1)`.
- **[`codigos_py/1.4_qh_pf_a_partir_do_gtfs.py`](../codigos_py/1.4_qh_pf_a_partir_do_gtfs.py)**: valida antes da gravação que todas as bandas `(linha, headsign, start, end, headway)` e o total de partidas foram preservados entre entrada e saída, além de checar o total expandido no Excel. Divergências encerram o processo com `SystemExit(1)`.

### Checagens de integridade em `2`, `5`, `5.1` e `6`

- **[`codigos_py/2_ajustar_stop_times.py`](../codigos_py/2_ajustar_stop_times.py)**:
  - Exporta `shape_dist_negativos.csv` caso detecte registros com `shape_dist_traveled < 0`.
  - Verifica ausência de valores vazios/nulos em `arrival_time` e `departure_time` ao final do recálculo; se houver inconsistências, salva `relatorio_inconsistentes_<timestamp>.csv` e interrompe a execução com `ValueError("Processamento interrompido devido a inconsistências.")`.
- **[`codigos_py/5_juntar_gtfs.py`](../codigos_py/5_juntar_gtfs.py) e [`codigos_py/5.1_juntar_gtfs_sppo.py`](../codigos_py/5.1_juntar_gtfs_sppo.py)**:
  - Verificam horários vazios em `stop_times.txt` nas entradas (SPPO e, no script `5`, BRT) e no GTFS combinado final, interrompendo com `ValueError` caso algum registro esteja vazio.
  - Detectam e removem shapes com menos de 2 pontos antes de consolidar o GTFS.
- **[`codigos_py/6_gerar_shapes.py`](../codigos_py/6_gerar_shapes.py)**:
  - Identifica shapes com menos de 2 pontos e, quando há trips associadas a esses shapes, grava `shapes_invalidos_com_trips.csv` antes de descartá-los da geração dos `LineString`.

---

## Validação externa (`validacao_gtfs`)

A validação estrutural de arquivos GTFS (pré e pós-pipeline) e as comparações de conteúdo entre Ordens de Serviço (OS) e GTFS são mantidas em um repositório irmão separado: `C:\github_repositories\validacao_gtfs`. Os antigos scripts da família `11*` foram removidos deste repositório e migrados para lá.

| Script em `validacao_gtfs` | Finalidade |
| --- | --- |
| `0_validar_gtfs_entrada.py` | Validação pré-pipeline do GTFS de entrada antes de executar o script `2`. |
| `1_validar_gtfs.py` | Validação estrutural e de qualidade pós-pipeline do GTFS gerado. |
| `2_comparar_os_gtfs.py` | Comparação de partidas entre OS (`OS.csv`) e GTFS (`GTFS.zip`) para todos os tipos de dia. |
| `3_comparar_duas_os.py` | Comparação entre duas OS no formato "Resumo por Dia". |
| `4_comparar_dois_gtfs.py` | Comparação entre dois arquivos GTFS com cálculo de extensão GIS. |

Consulte também:
- [Fluxo do Pipeline](./pipeline.md) para localizar onde cada validação se encaixa no fluxo de trabalho.
- [Solução de Problemas](./troubleshooting.md) para diagnóstico quando um gate ou validação falhar.
- [Catálogo de Scripts](./scripts_reference.md) para detalhes de entrada e saída de cada script.
