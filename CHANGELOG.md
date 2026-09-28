# Changelog — Processar GTFS

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

## [Não lançado] - 2026-09-28

### Adicionado
- Novo script `codigos_py/1.2_combinar_quadros_horarios.py`:
  - Combina quadros de horários entre diferentes serviços/calendários com recorte por faixa de horário.
  - Permite gerar novos quadros de domingo (`D_REG`) aproveitando faixas de dia útil (`U_REG`) entre 06:00:00 e 20:00:00 (exclusivo).
  - Preserva faixas de madrugada e noite do serviço de destino original, com ajuste fino de bordas (*clipping*) nos limites configurados.
  - Suporta linhas sem quadro de destino prévio, gerando o quadro a partir da faixa importada.
  - Saída no formato idêntico ao script 1 (`trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs`), salva em pasta dedicada (`qh_por_linha_combinado/...`).
  - Suporta execução via `--config <arquivo_json>` ou string JSON inline.
  - Validado com dados reais da linha 378.
- Novo script `codigos_py/1.1_extrair_qh_partidas.py`:
  - Extrai quadros de horários com partidas detalhadas de cada viagem a partir do GTFS.
  - Suporta viagens expandidas via `frequencies.txt` e viagens regulares com partidas em `stop_times.txt`.
  - Calcula a ordem de partida (`ordem_partida`: 1, 2, 3...) e o intervalo em minutos em relação à viagem anterior (`intervalo_min`).
  - Exporta arquivos CSV individuais organizados e sanitizados por linha, sentido/letreiro e calendário/serviço (`partidas_{servico}_{vista}_{calendario}.csv`).
  - Compatível com passagem de parâmetros via JSON (`--config <json>`) e execução autônoma via terminal.
  - Validado com dados reais do GTFS combinado `gtfs_combi_2026-09-01Q.zip` para 23 linhas (gerando 123 arquivos CSV e 5.969 partidas exportadas com sucesso).
