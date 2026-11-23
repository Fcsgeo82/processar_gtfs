# Solução de Problemas (Troubleshooting)

Este documento reúne erros conhecidos, causas prováveis, formas de diagnóstico e procedimentos de correção observados no código e no histórico operacional do `processar_gtfs`.

## Índice

1. [`PermissionError` ao carregar quadros de horários (`1.5` / `app_carregar_qh`)](#1-permissionerror-ao-carregar-quadros-de-horários-15--app_carregar_qh)
2. [Falha no teste dbt `unique: [feed_start_date, id_viagem]` ou duplicação de `trip_id`](#2-falha-no-teste-dbt-unique-feed_start_date-id_viagem-ou-duplicação-de-trip_id)
3. [`ValueError: Processamento interrompido devido a inconsistências` em `2_ajustar_stop_times.py`](#3-valueerror-processamento-interrompido-devido-a-inconsistências-em-2_ajustar_stop_timespy)
4. [`ValueError` de horários vazios em `5_juntar_gtfs.py` ou `5.1_juntar_gtfs_sppo.py`](#4-valueerror-de-horários-vazios-em-5_juntar_gtfspy-ou-51_juntar_gtfs_sppopy)
5. [`FileNotFoundError` ou `KeyError` em insumos e tabelas GTFS](#5-filenotfounderror-ou-keyerror-em-insumos-e-tabelas-gtfs)
6. [Falha de gate (`SystemExit(1)`) ou `ValueError` em `1.3`, `1.3.1` ou `1.4`](#6-falha-de-gate-systemexit1-ou-valueerror-em-13-131-ou-14)
7. [`sys.exit(1)` em `9_filtrar_gtfs_por_lista.py` (nenhuma trip correspondeu à lista)](#7-sysexit1-em-9_filtrar_gtfs_por_listapy-nenhuma-trip-correspondeu-à-lista)
8. [Relatório `shapes_invalidos_com_trips.csv` em `6_gerar_shapes.py`](#8-relatório-shapes_invalidos_com_tripscsv-em-6_gerar_shapespy)
9. [Extensão de linha inflada ou divergente de `shape_dist_traveled`](#9-extensão-de-linha-inflada-ou-divergente-de-shape_dist_traveled)
10. [Erro de codificação no console Windows ou alocação de memória ao gravar Parquet](#10-erro-de-codificação-no-console-windows-ou-alocação-de-memória-ao-gravar-parquet)
11. [Scripts descontinuados ou com erros conhecidos (não usar em produção)](#11-scripts-descontinuados-ou-com-erros-conhecidos-não-usar-em-produção)

---

## 1. `PermissionError` ao carregar quadros de horários (`1.5` / `app_carregar_qh`)

- **Sintoma / Mensagem de erro**: `PermissionError` lançada por [`codigos_py/1.5_carregar_qh_no_gtfs.py`](../codigos_py/1.5_carregar_qh_no_gtfs.py) ou [`src/gtfs_carregar_qh.py`](../src/gtfs_carregar_qh.py) ao aplicar quadros no GTFS.
- **Possível causa**: um ou mais arquivos CSV de quadro de horários foram classificados como `REQUER_CLONAGEM` porque a linha não possui viagem cadastrada no calendário alvo (por exemplo, `F_REG`) no GTFS base, e o parâmetro `permitir_clonagem` está definido como `False` (valor padrão de segurança).
- **Como identificar**: o relatório prévio de detecção (exibido no log do CLI ou na tabela de pré-visualização de [`src/app_carregar_qh.py`](../src/app_carregar_qh.py)) marca o quadro com status `REQUER_CLONAGEM` e informa o `molde_service_id` sugerido (normalmente `U_REG`).
- **Solução recomendada**:
  1. Revise os quadros marcados como `REQUER_CLONAGEM` para confirmar se a clonagem da viagem molde (itinerário e `stop_times`) a partir de `U_REG` é desejada para aquelas linhas.
  2. Se confirmado, habilite a opção de autorização na interface Streamlit ou defina `"permitir_clonagem": true` no JSON de `--config` (ou na variável correspondente do script `1.5`).

---

## 2. Falha no teste dbt `unique: [feed_start_date, id_viagem]` ou duplicação de `trip_id`

- **Sintoma / Mensagem de erro**: falha no teste dbt `unique: [feed_start_date, id_viagem]` do modelo `viagem_planejada_planejamento`, ou multiplicação indevida de partidas ao expandir o GTFS.
- **Possível causa**: violação do invariante 1:1 entre `trips.txt` e `frequencies.txt` (múltiplas faixas horárias em `frequencies.txt` compartilhando o mesmo `trip_id`), ou presença de trips duplicadas/órfãs após fusão manual de tabelas GTFS.
- **Como identificar**:
  - Verificar se `frequencies["trip_id"].is_unique` e `trips["trip_id"].is_unique` são verdadeiros no GTFS gerado.
  - Conferir se cada banda em `frequencies.txt` possui registro exclusivo em `trips.txt` e `stop_times.txt`, com o `departure_time` da primeira parada alinhado ao `start_time` da faixa.
  - Executar a suíte [`tests/test_gtfs_carregar_qh.py`](../tests/test_gtfs_carregar_qh.py) para garantir que a lógica do carregador preserva a unicidade.
- **Solução recomendada**:
  - Para carregar quadros de horários no GTFS, utilize sempre [`codigos_py/1.5_carregar_qh_no_gtfs.py`](../codigos_py/1.5_carregar_qh_no_gtfs.py) ou [`src/app_carregar_qh.py`](../src/app_carregar_qh.py), que criam um `trip_id` exclusivo por banda e executam `clean_gtfs()`.
  - Para remover duplicatas em linhas regulares de um GTFS já combinado (preservando `EXCEP` e desvios), execute [`codigos_py/5.4_eliminar_duplicatas_gtfs.py`](../codigos_py/5.4_eliminar_duplicatas_gtfs.py).

---

## 3. `ValueError: Processamento interrompido devido a inconsistências` em `2_ajustar_stop_times.py`

- **Sintoma / Mensagem de erro**: `ValueError: Processamento interrompido devido a inconsistências.` ao final da execução de [`codigos_py/2_ajustar_stop_times.py`](../codigos_py/2_ajustar_stop_times.py).
- **Possível causa**: após o recálculo dos tempos de percurso por velocidades GPS, restaram registros em `stop_times.txt` com `arrival_time` ou `departure_time` vazios/nulos, ou inconsistências prévias de `shape_dist_traveled` (valores negativos ou ausentes) no GTFS de entrada.
- **Como identificar**:
  - Inspecione o arquivo `relatorio_inconsistentes_<YYYYMMDD_HHMMSS>.csv` gerado no diretório de trabalho no momento do erro para listar os `trip_id` e paradas afetadas.
  - Verifique se também foi gerado `shape_dist_negativos.csv`, indicando distâncias negativas em `stop_times.txt`.
- **Solução recomendada**:
  1. Corrija os registros inconsistentes no GTFS de origem (ou valide-o previamente com `0_validar_gtfs_entrada.py` no projeto irmão `validacao_gtfs`).
  2. Verifique se o `calendario.json` e os arquivos de viagens GPS (Parquet/CSV) do período existem e estão íntegros antes de reexecutar o script `2`.

---

## 4. `ValueError` de horários vazios em `5_juntar_gtfs.py` ou `5.1_juntar_gtfs_sppo.py`

- **Sintoma / Mensagem de erro**:
  - `ValueError: ⛔ SPPO processado está com horários vazios.`
  - `ValueError: ⛔ BRT processado está com horários vazios.` (em `5_juntar_gtfs.py`)
  - `ValueError: ⛔ ERRO: GTFS combinado tem stops com horários vazios!` (em `5_juntar_gtfs.py`) ou `ValueError: ⛔ ERRO: GTFS tem stops com horários vazios!` (em `5.1_juntar_gtfs_sppo.py`)
- **Possível causa**: um dos arquivos GTFS `_PROC.zip` fornecidos na entrada possui `stop_times.txt` com `arrival_time` ou `departure_time` vazios/nulos (geralmente por ter pulado o script `2` ou utilizado um arquivo intermediário corrompido).
- **Como identificar**: o log imediatamente anterior à exceção informa a quantidade exata de registros em `stop_times` com horários vazios e em qual modal (SPPO, BRT ou combinado) o problema ocorreu.
- **Solução recomendada**:
  - Reexecute [`codigos_py/2_ajustar_stop_times.py`](../codigos_py/2_ajustar_stop_times.py) para o modal afetado até concluir sem inconsistências, garantindo que o `_PROC.zip` de saída não contenha horários vazios antes de rodar `5` ou `5.1`.

---

## 5. `FileNotFoundError` ou `KeyError` em insumos e tabelas GTFS

- **Sintoma / Mensagem de erro**: `FileNotFoundError` ao abrir arquivos ZIP, diretórios de viagens GPS, `calendario.json`, `gtfs_cores.csv` ou arquivos de substituição; ou `KeyError` ao acessar tabelas como `trips.txt`, `frequencies.txt`, `routes.txt` ou colunas esperadas dentro do ZIP.
- **Possível causa**:
  - `BASE_DADOS` ou parâmetros de `ano`, `mes` e `estudo` (quinzena) não correspondem à estrutura real de pastas em `C:/R_SMTR/dados` e `C:/R_SMTR/resultados`.
  - Insumo auxiliar ausente (como `gtfs_cores.csv`, `calendario.json` ou pasta de arquivos de substituição em `5`/`5.1`).
  - Arquivo GTFS de entrada incompleto (sem tabela obrigatória para aquela etapa, por exemplo `frequencies.txt` ou `trips.txt`).
- **Como identificar**:
  - Confira no traceback o caminho exato que não foi localizado ou a chave ausente no dicionário GTFS/DataFrame.
  - Compare o caminho esperado com a convenção documentada em [Configurações](./configuration.md) e [Dados e Artefatos](./data_dictionary.md).
- **Solução recomendada**:
  - Ajuste `BASE_DADOS`, `ano`, `mes`, `estudo` ou o caminho explícito no JSON `--config` (ou na sidebar de `src/app.py`).
  - Garanta que os insumos auxiliares existam nos diretórios esperados e que o GTFS de entrada contenha todas as tabelas exigidas pela etapa.

---

## 6. Falha de gate (`SystemExit(1)`) ou `ValueError` em `1.3`, `1.3.1` ou `1.4`

- **Sintoma / Mensagem de erro**:
  - `!!! GATE FALHOU:` seguido de `SystemExit(1)` em [`codigos_py/1.3_qh_a_partir_de_partidas.py`](../codigos_py/1.3_qh_a_partir_de_partidas.py) ou [`codigos_py/1.4_qh_pf_a_partir_do_gtfs.py`](../codigos_py/1.4_qh_pf_a_partir_do_gtfs.py).
  - `!!! Excel: total expandido (...) != partidas de saída (...)` (`SystemExit(1)`).
  - `!!! CONFERÊNCIA FALHOU` (`SystemExit(1)`) em [`codigos_py/1.3.1_conferir_partidas_geradas.py`](../codigos_py/1.3.1_conferir_partidas_geradas.py).
  - `ValueError` na leitura da tabela de entrada de `1.3` / `1.3.1` (contagem não numérica com `traco_ausente='erro'`, `vista` sem separador `' - '`, linhas duplicadas em `(servico, sentido, faixa)`, sentido/faixa fora do domínio ou colisão de nome de arquivo sanitizado).
- **Possível causa**:
  - Células com traço (`-`) ou texto na tabela de contagens enquanto `traco_ausente` está configurado como `'erro'`.
  - Contagens com casas decimais ou formato não inteiro ao rodar `1.3.1` (o script `1.3` normaliza vírgula e arredonda decimais, enquanto `1.3.1` exige inteiros puros na tabela de entrada).
  - Valor da coluna `vista` sem o separador `' - '` para sentidos `Ida` ou `Volta`, impedindo derivar o `trip_headsign`.
  - Filtros de `1.4` resultando em zero bandas (`"Nenhuma banda de frequência sobrou após os filtros"`).
  - Arquivos antigos de execuções anteriores misturados na `pasta_saida` ao rodar `1.3.1` (gerando anomalias `ORFAO` ou `SOBRANDO`).
  - Colisão de nomes de arquivo após sanitização de `servico` e `headsign`.
- **Como identificar**:
  - Leia a mensagem específica impressa antes do `SystemExit(1)` ou `ValueError`.
  - Em `1.3.1`, abra `relatorio_conferencia_partidas.csv` e `_conferencia_resumo.txt` na pasta conferida e filtre por `status == 'ANOMALIA'` ou `status == 'DIVERGENTE'`.
- **Solução recomendada**:
  - Para traços/vazios esperados em `1.3`, utilize `traco_ausente='zerar'` (padrão) e garanta valores inteiros na entrada antes de auditar com `1.3.1`.
  - Corrija valores de `vista` (`Origem - Destino`) e remova duplicatas de `(servico, sentido, faixa)` na tabela de entrada.
  - Em `1.3.1`, verifique se `linhas_rodar` e `service_id` correspondem exatamente aos parâmetros usados na geração e execute `1.3` em uma pasta limpa quando houver arquivos residuais (`ORFAO`).

---

## 7. `sys.exit(1)` em `9_filtrar_gtfs_por_lista.py` (nenhuma trip correspondeu à lista)

- **Sintoma / Mensagem de erro**: log `⛔ Nenhuma trip correspondeu à lista de filtro. Saindo sem gerar arquivo.` seguido de encerramento com código `1`.
- **Possível causa**: nenhuma viagem do GTFS de entrada satisfez simultaneamente o filtro de `CALENDARIOS_ALVO` (padrão `EXCEP`) e a chave composta de 5 campos (`trip_short_name` + `route_long_name` + `agency_name` + `direction_id` + evento extraído de `[...]` em `trip_headsign`). Causas frequentes:
  - Separador incorreto na lista de filtro (CSV separado por `,` quando o script espera TSV separado por `\t`, ou vice-versa).
  - Divergência no valor de `CALENDARIOS_ALVO` em relação aos `service_id` reais do GTFS.
  - Diferença de grafia no nome do evento dentro dos colchetes `[evento]` em `trip_headsign`, no consórcio (`agency_name`) ou na vista (`route_long_name`).
- **Como identificar**: o script lista no log todas as entradas da lista que não tiveram match (`✗ Serviço | Vista | Consórcio | Sentido | Evento`).
- **Solução recomendada**:
  1. Confira o delimitador da lista de filtro e confirme que as colunas `Serviço`, `Vista`, `Consórcio`, `Sentido` e `Evento` estão corretamente separadas.
  2. Verifique no `trips.txt` do GTFS se os `service_id` correspondem a `CALENDARIOS_ALVO` e se o texto entre `[...]` em `trip_headsign` coincide com a coluna `Evento`.

---

## 8. Relatório `shapes_invalidos_com_trips.csv` em `6_gerar_shapes.py`

- **Sintoma / Mensagem de erro**: log `Total inválidos: N` seguido de `Relatório salvo em 'shapes_invalidos_com_trips.csv'` durante a execução de [`codigos_py/6_gerar_shapes.py`](../codigos_py/6_gerar_shapes.py).
- **Possível causa**: existem `shape_id` em `shapes.txt` com menos de 2 pontos geográficos, o que impede a construção de geometrias `LineString` válidas pelo `shapely`.
- **Como identificar**: inspecione `shapes_invalidos_com_trips.csv` gerado no diretório de trabalho para identificar quais viagens (`trips.txt`) referenciam os `shape_id` descartados.
- **Solução recomendada**:
  - O script descarta automaticamente esses shapes inválidos para não interromper a exportação dos Shapefiles/GeoPackages, mas as linhas listadas no CSV ficarão sem geometria correspondente.
  - Corrija os shapes no GTFS de origem (ou verifique se foram filtrados corretamente nas etapas `5` / `5.1`) e reexecute o script `6`.

---

## 9. Extensão de linha inflada ou divergente de `shape_dist_traveled`

- **Sintoma / Mensagem de erro**: valores de extensão em metros aparentemente inflados em comparações históricas, ou diferença pequena (~21 m) entre a extensão gerada pelo pipeline e o campo `shape_dist_traveled` do GTFS.
- **Possível causa**:
  - **Extensão inflada**: inclusão indevida de trips de excepcionalidade (`EXCEP`) ou desvios (`[` no `trip_headsign`) antes do cálculo do máximo por itinerário — o `max()` acaba selecionando o shape de desvio/exceção mais longo.
  - **Diferença em relação a `shape_dist_traveled`**: o pipeline calcula a extensão por comprimento geográfico GIS (`LineString` projetado em `EPSG:31983`, truncado com `astype(int)`), regra validada pelo histórico do Sigmob, que fica tipicamente ~21 m abaixo de `shape_dist_traveled`.
- **Como identificar**: verifique se o cálculo foi feito com os scripts atualizados (`7_lista_partidas.py`, `8_gerar_extensoes.py`, `8.1_gerar_extensoes_rio.py`), todos alinhados à regra de excluir `EXCEP` e `[` no `trip_headsign` antes de aplicar o máximo por itinerário.
- **Solução recomendada**:
  - Utilize os scripts `7`, `8` ou `8.1` do repositório sem remover o filtro de exclusão de `EXCEP` e desvios.
  - Considere a diferença de ~21 m frente a `shape_dist_traveled` como comportamento esperado da projeção GIS em `EPSG:31983` (note que o script `7` não filtra `route_type` na extensão para cobrir o BRT `702`, enquanto `8` e `8.1` filtram `[3, 700]` para listagem só-SPPO).

---

## 10. Erro de codificação no console Windows ou alocação de memória ao gravar Parquet

- **Sintoma / Mensagem de erro**:
  - `UnicodeEncodeError` ao executar scripts diretamente no terminal Windows com codepage ANSI (`cp1252`), devido a caracteres Unicode/box-drawing nos logs (`╔═╗`, `✓`, `⛔`).
  - `[Errno 22] Invalid argument` ao gravar arquivos `.parquet` via `pyarrow` em DataFrames grandes com colunas de tipo misto (`object` com `str`, `NaN` e `Timedelta`).
- **Possível causa**:
  - No Windows, `stdout` de subprocessos herda `cp1252` se `PYTHONIOENCODING` não estiver definido.
  - O `pyarrow` no Windows pode falhar na alocação de memória ao serializar colunas `object` heterogêneas em Parquet.
- **Como identificar**:
  - `UnicodeEncodeError: 'charmap' codec can't encode character ...` no terminal ao rodar via CLI fora do app Streamlit.
  - `OSError: [Errno 22] Invalid argument` durante a escrita com `to_parquet`.
- **Solução recomendada**:
  - **Codificação**: via interface Streamlit, [`src/runner.py`](../src/runner.py) já define `PYTHONIOENCODING="utf-8"` automaticamente. Ao rodar diretamente pelo PowerShell/CMD, defina a variável antes do comando:
    ```powershell
    $env:PYTHONIOENCODING = "utf-8"
    python codigos_py/<script>.py --config caminho/para/config.json
    ```
  - **Parquet**: [`codigos_py/7_lista_partidas.py`](../codigos_py/7_lista_partidas.py) já mitiga o erro convertendo colunas `object` e `timedelta64` para string pura (`fillna("").astype(str)`) antes de chamar `to_parquet(..., engine='pyarrow')`. Se o erro ocorrer em adaptações futuras, aplique a mesma conversão antes da gravação.

---

## 11. Scripts descontinuados ou com erros conhecidos (não usar em produção)

- **Sintoma / Mensagem de erro**: resultados incorretos em resumos de OS ou comportamento obsoleto ao tentar executar scripts legados diretamente pelo terminal.
- **Possível causa**: dois scripts permanecem no repositório apenas por histórico/referência e não devem ser usados em rotinas produtivas:
  - [`codigos_py/3_desvios_nao-utilizar.py`](../codigos_py/3_desvios_nao-utilizar.py): descontinuado e não exposto na interface Streamlit.
  - [`codigos_py/7.1_resumo_os_domingo_du.py`](../codigos_py/7.1_resumo_os_domingo_du.py): contém erros conhecidos (mantido apenas para referência; ainda acessível na aba 7 → modo 7.1, mas deve ser evitado).
- **Como identificar**: avisos explícitos no código e na documentação de referência dos scripts.
- **Solução recomendada**:
  - Para levantamento de desvios/excepcionalidades, utilize [`codigos_py/4_trajetos_alternativos.py`](../codigos_py/4_trajetos_alternativos.py) (e [`codigos_py/9_filtrar_gtfs_por_lista.py`](../codigos_py/9_filtrar_gtfs_por_lista.py) + [`codigos_py/10_juntar_dois_gtfs.py`](../codigos_py/10_juntar_dois_gtfs.py) para geração de GTFS filtrado/combinado).
  - Para combinar partidas entre Dia Útil e Domingo, utilize [`codigos_py/7.2_combinador_partidas.py`](../codigos_py/7.2_combinador_partidas.py) (ou [`codigos_py/1.2_combinar_quadros_horarios.py`](../codigos_py/1.2_combinar_quadros_horarios.py) para combinação por faixas de frequência).

---

Consulte também:
- [Testes e Validações](./testing.md) para detalhes sobre gates e auditoria `1.3.1`.
- [Configurações](./configuration.md) para conferir parâmetros `--config` e caminhos padrão.
- [Catálogo de Scripts](./scripts_reference.md) para verificar requisitos específicos de cada etapa.
