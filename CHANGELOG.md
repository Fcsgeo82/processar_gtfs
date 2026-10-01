# Changelog — Processar GTFS

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado no [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

## [Não lançado] - 2026-09-28

### Adicionado
- Novo script `codigos_py/7.1_resumo_os_domingo_du.py`:
  - Combina partidas de diferentes tipos de dia no formato da tabela de OS, gerando um resumo de partidas por faixa horária para Domingo a partir da base consolidada do Script 7 (`partidas.parquet` ou `partidas.csv`).
  - Importa viagens de Dia Útil (`tipo_dia == 'du'`) na janela 06:00:00 às 20:00:00 e preserva viagens de Domingo (`tipo_dia == 'dom'`) na madrugada e noite.
  - Pivota os dados pelas 14 faixas horárias operacionais padrão, intercalando colunas de Partidas e Quilometragem em branco.
  - Exporta resultados em Excel (`.xlsx`) e CSV (`utf-8-sig`, delimitador `;`).
- Novo script `codigos_py/7.2_combinador_partidas.py`:
  - Combina partidas de diferentes tipos de dia no formato do arquivo de partidas gerado pelo Script 7.
  - Gera um arquivo de partidas consolidado para Domingo: mantém a madrugada e a noite do Domingo e substitui o bloco diurno (06:00:00–20:00:00, exclusivo) pelas partidas de Dia Útil.
  - Compatibiliza o campo `intervalo` nas transições entre os blocos (05:59→06:00 e 19:59→20:00).
  - Exporta no mesmo formato do Script 7 (`trip_short_name`, `direction_id`, `departure_time`, `intervalo`, etc.).
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
