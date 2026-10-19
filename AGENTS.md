# AGENTS.md — Memória de sessão (Processar GTFS)

Arquivo auto-carregado em toda sessão. Mantenha atualizado e conciso.
Para histórico detalhado, ver `.opencode/memory.md`.

## Projeto
Pipeline de processamento/validação de GTFS do transporte público do Rio
(ajustar stop_times por GPS, combinar modais SPPO/BRT/Rio, gerar shapes,
partidas, extensões e GTFS filtrados). Python + `pandas`/`geopandas`; orquestrado
por aplicação Streamlit (`src/app.py`). Contém versões antigas em R (`codigos_R/`).

## Estrutura
- `src/app.py`: interface Streamlit com abas para cada etapa do pipeline.
- `src/runner.py`: executa scripts como subprocesso passando `--config <json>`;
  barra de progresso por tempo decorrido e logs em tempo real.
- `src/tabs/tab_*.py`: uma aba por etapa (QH, ajustar ST, alternativos,
  juntar, shapes, partidas, extensões, filtrar, juntar dois).
- `codigos_py/`: scripts Python do pipeline, numerados 1 a 10
  (`1_extrair_qh_especificado_no_gtfs` [faixas de frequência],
  `1.1_extrair_qh_partidas` [grade de partidas detalhadas],
  `1.2_combinar_quadros_horarios` [combina faixas entre serviços/dias por horário],
  `1.3_qh_a_partir_de_partidas` [QH factíveis a partir de tabela de contagens
  por linha/sentido/faixa — aceita formato longo (Faixa+Partidas) ou wide
  (uma coluna por faixa, melt automático); headsign derivado da vista;
  exporta CSVs por quadro + Excel com uma aba por linha; default F_REG;
  sem aba Streamlit ainda — CLI/`--config`],
  `1.3.1_conferir_partidas_geradas` [conferência independente dos quadros do 1.3
  contra a entrada — reexpande bandas, compara (servico,sentido,faixa), confere
  Excel; relatório + exit 0/1; sem aba Streamlit],
  `1.4_qh_pf_a_partir_do_gtfs` [quadros de ponto facultativo (`F_REG`) direto do
  `frequencies.txt` de um GTFS (default `0171_gtfs_out_26_1E_ret.zip` na raiz);
  filtra `route_type=700`, exclui agência MOBI-Rio (`20001`) inteira; base DU
  (`U_REG`) p/ Internorte/Intersul/Transcarioca/Santa Cruz e sábado (`S_REG`) p/
  GTU/TUSE; saída própria `qh_por_linha_pf_gtfs/{estudo}Q/` com CSVs + Excel +
  gate; sem aba Streamlit],
  `2_ajustar_stop_times`, `4_trajetos_alternativos`, `5_juntar_gtfs` e variantes 5.1–5.4,
  `6_gerar_shapes`, `7_lista_partidas` + 7.1 + 7.2 (tipos de dia `du`/`sab`/`dom`/`pf`
  [ponto facultativo, `F_REG`]; `get_pattern` lança `ValueError` p/ token desconhecido),
  `8_gerar_extensoes` + 8.1,
  `9_filtrar_gtfs_por_lista`, `10_juntar_dois_gtfs`).
- Projeto irmão `C:\github_repositories\validacao` (independente, sem git): os
  validadores `0_validar_gtfs_entrada.py` (pró-pipeline) e `validar_gtfs.py`
  (pós-pipeline, cruza GTFS × OS) saíram daqui em 2026-10-06; tem `README.md`
  e `CHANGELOG.md` próprios.
- `codigos_R/`: versões antigas do pipeline em R (`datados/` = obsoletos).
- `validacao/`: scripts de validação pós-pipeline GTFS e cruzamento com OS (`validar_gtfs.py`).
- `Iniciar_App.bat`: atalho de inicialização da aplicação.
- `CONTEXTO.md`, `CAPABILITIES_AND_AGENTS.md`, `plano_de_implementacao.md`: docs.
- `PLANO_1.3_qh_a_partir_de_partidas.md`: plano pronto para execução (2026-10-02) do
  script `1.3` — gerar QH no formato do script 1 a partir da lista de partidas do 7/7.2.
  Invariante: contagem de partidas por faixa preservada; headway regularizado.
  Atenção: agrupar por `(ciclo, faixa)`, nunca só por `faixa` (a faixa dá a volta em 24h).

## Convenções
- Scripts aceitam `--config <json>` e mantêm retrocompatibilidade com variáveis
  hardcoded no topo (`BASE_DADOS`, ano, mês, estudo).
- Leitura de CSVs/GTFS com `dtype=str`.
- `clean_gtfs()` = limpeza em cascata (remove registros órfãos), equivalente ao
  `gtfstools::filter_by_trip_id`.
- Projeção geográfica: EPSG:31983. Saídas em `resultados/` e `dados/`.
- Docs e comentários em português. Execução: `python -m streamlit run src/app.py`.

## Memória: como usar
- Sessão começa: ler `AGENTS.md` (já carregado) e, se pedido, `.opencode/memory.md`.
- Ao terminar tarefa relevante: atualizar `AGENTS.md` (estado atual) e
  `.opencode/memory.md` (histórico) antes de encerrar.
- NUNCA registrar segredos/credenciais nestes arquivos.