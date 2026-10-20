# Memória de longo prazo — Processar GTFS

Registro de decisões, histórico e contexto detalhado. Complementa o `AGENTS.md`.
Preferência: adicionar entradas no topo, datadas.

---

## 2026-10-20 — `trip_id` vazio nos quadros é por design (Sigmob); "decimais" no 7 = segundos do GPS

- **Confirmado pelo usuário:** a coluna `trip_id` dos CSVs de QH sai **vazio por
  design** — é preenchida ao subir o quadro no sistema **Sigmob** e salvar. Nada
  a corrigir no 1.2 (nem no 1): `1_extrair_qh_especificado_no_gtfs.py:95` já
  grava `trip_id = ""`, e o 1.2 só preserva o formato de 6 colunas (cabeçalho
  espelha o `frequencies.txt`). Nenhum script do `codigos_py/` lê
  `qh_por_linha_combinado` — o consumo é Sigmob/manual.
- **Diagnóstico (sem alteração, decisão do usuário de mudar de assunto):**
  "partidas com decimais" no script 7 são **segundos ≠ 00** vindos do
  `stop_times.txt` ajustado por GPS (script 2), herdados verbatim pelas linhas
  regulares (`7_lista_partidas.py:201-206`); ex.: 2.472 de 147.554 no
  `partidas_2026-10-02Q.csv`. Frequências ficam limpas (headways múltiplos de
  60). Correção proposta e **não aplicada**: `.round('min')` após
  `horario_to_timedelta`.
- **Defaults do 1.2 alterados pelo usuário (não commitados):** `ano_gtfs`
  2029→2030, `estudo_gtfs` 01→02, `hora_fim` 20:00→21:00, `linhas_rodar` lista
  fixa → `[]` (todas as linhas).

---

## 2026-10-16 — Script 7: novo tipo de dia `pf` (ponto facultativo)

- Pedido: o script 7 passar a **ler e criar mais um calendário na saída — ponto
  facultativo** — além de `du`/`sab`/`dom`. Definições confirmadas com o usuário:
  token **`pf`**, entra no **default** de `tipos_dia`, caminho do GTFS **literal
  `gtfs/2026/gtfs_combi_2026-10-02Q_RIO.zip`**, default da aba também atualizado.
- Mudanças (`codigos_py/7_lista_partidas.py`): `get_pattern('pf')→'F'`
  (casa só com `F_REG` no GTFS atual); `tipos_dia` default `['du','sab','dom','pf']`;
  default de `endereco_gtfs` literal 2026 (o antigo interpolava `ano_gtfs`, cujo
  default `2030` não resolve); `--config` com `utf-8-sig` (BOM quebra `json.load`);
  **guard**: tipo desconhecido → `ValueError` (antes `return ''` fazia
  `str.contains('')` casar com todos os trips).
- Aba `src/tabs/tab_7_partidas.py`: default do campo GTFS →
  `gtfs_combi_2026-10-02Q_RIO.zip` (literal 2026, `ano` da sessão pode ser 2030;
  variável `ano` ficou sem uso e foi removida) + `pf` no multiselect.
- **Verificação (temp, não toca `resultados/partidas`):** reexpansão independente
  de `frequencies.txt` por `service_id` bate nos 4 tipos: du 2.165 (U_REG),
  sab 2.021 (S_REG), dom 1.930 (D_REG), **pf 2.021 (F_REG, 410 trips)** — sem
  vazamento. Coincidência pf=sab=2.021 é real na origem (`S_REG` também expande
  2.021); arquivos diferem (`iguais=False`). Guard `['foo']` → exit 1.
- `7.1`/`7.2` filtram `tipo_dia=='du'/'dom'` → ignoram `pf` (não precisaram de
  mudança). `EXCEP` continua fora (nenhum padrão casa com ele).
- Docs: README seção 7 (entrada/tipos/saídas), CHANGELOG `2026-10-16`, AGENTS.

---

## 2026-10-16 — Script 1.3.1: conferência independente das contagens (SPPO e RIO)

- Criado `codigos_py/1.3.1_conferir_partidas_geradas.py` a pedido do usuário
  ("confirmar se os quadros gerados estão com o mesmo número de partidas do
  arquivo de entrada"): relê a entrada e os `horarios_*.csv` **do disco**,
  reexpande as bandas (`n=(end−start)/headway`) e compara por
  (servico, sentido, faixa); não confia nos artefatos da geração.
- Anomalias: `FALTANDO`/`SOBRANDO`/`ÓRFÃO`, `BANDA` (headway<1, não divisível,
  start fora da faixa, end vaza), `CELULA` (Δ), `EXCEL` (blocos vs expansão).
  Relatório `relatorio_conferencia_partidas.csv` + `_conferencia_resumo.txt`
  na pasta conferida; exit 0/1.
- **Execuções (2026-10-16):**
  - RIO (`partidas_pf_rio_como_sabado.csv` → `.../RIO/10/qh_por_linha_partidas/01Q`):
    574 células, 2.021/2.021 partidas, 41 blocos Excel — **0 anomalias**.
  - SPPO (`partidas_pf_sppo_como_du.csv` → `.../SPPO/10/qh_por_linha_partidas/01Q`):
    10.766 células, 38.730/38.730 partidas, 768 blocos Excel — **0 anomalias**.
- **Teste negativo:** cópia da pasta RIO com a última banda da 804 encurtada →
  detectou `BANDA` (end<=start) + `CELULA` (delta −3), exit 1. Detecção confirmada.
- Detalhe de implementação: `headway_secs` nos CSVs do 1.3 é total de segundos
  (ex.: `3600`), não `HH:MM:SS` — o leitor aceita os dois formatos.

---

## 2026-10-15 — Documentação do script 1.3 atualizada

- `README.md`: nova seção `1.3_qh_a_partir_de_partidas.py` (tabela no padrão
  dos demais scripts) entre 1.2 e 2; nota: sem aba Streamlit, executar via CLI.
- `CHANGELOG.md`: entrada `## [Não lançado] - 2026-10-15` com criação do
  script + exportação Excel + suporte wide.
- `CONTEXTO.md`: sessão `2026-10-15` com resumo, decisões e pendência.
- `AGENTS.md`: marcada pendência "sem aba Streamlit ainda" no entry do 1.3.
- `PLANO_1.3_...md`: banner de EXECUTADO (plano original adaptado).
- **Fallback de headway confirmado pelo usuário:** se `dur//n` resultar em
  intervalo < 300s (`h==0`), o script usa o bruto `h0` — contagem sempre
  preservada, granularidade que cede. Decisão: **não alterar nada**.
- Pendência restante: **aba Streamlit** (`tab_1.3` + registro em `src/app.py`).

---

## 2026-10-15 — Script 1.3: aceita CSV em formato wide (uma coluna por faixa)

- Usuário reformatou a entrada e trocou o default para
  `partidas_pf_sppo_como_du.csv` (38.730 partidas, 410 serviços): agora é
  **wide** — uma linha por (servico, vista, consorcio, sentido) e uma coluna
  por faixa (`00:00-01:00` … `23:00-24:00`), em vez de longo (`Faixa` +
  `Partidas_Faixa`).
- Script agora **detecta o formato** após normalizar colunas: se faltarem
  `faixa`/`partidas_faixa`, localiza colunas cujo nome (sem espaços/`_`) casa
  com as 14 faixas padrão, renomeia para o rótulo canônico e faz **melt** para
  o formato longo — resto do pipeline idêntico nos dois casos. Ausência total
  dos dois formatos → erro listando as colunas lidas; faixas faltantes no wide
  → aviso.
- **Validado:** wide (769×18 → 10.766 linhas derretidas, 6.091 bandas,
  38.730 partidas, gate OK, soma independente das 14 colunas = 38.730) e
  retrocompatibilidade com o longo (`partidas_pf_rio.csv`, 41 grupos, gate OK).

---

## 2026-10-15 — Script 1.3: exportação Excel dos quadros (uma aba por linha)

- Adicionado ao `codigos_py/1.3_qh_a_partir_de_partidas.py` (após os CSVs) a
  geração de um workbook `.xlsx` na mesma pasta de saída:
  - **Uma aba por linha** (servico; nome de aba sanitizado, ≤31 chars, único);
    **um bloco por quadro** (sentido/headsign, ordem Ida → Volta → Circular):
    cabeçalho em negrito `Linha | valor | Trip headsign | valor | Tipo dia |
    valor`, linha em branco, tabela `Partida | Horário | Intervalo`.
  - **Partidas expandidas** das bandas (uma linha por partida, chronolog);
    `Horário` HH:MM:SS; `Intervalo` HH:MM:SS desde a partida anterior, primeira
    `--` (mesmo estilo script 7).
  - **Gate Excel:** total expandido == total de partidas de saída (aborta se
    divergir). Configs novos: `gerar_excel` (default True), `nome_excel`
    (default `quadros_partidas_{service_id}.xlsx`), `tipo_dia` (default =
    service_id, ex. `F_REG`).
  - Observação: pandas 3.0 removeu `GroupBy.items()` — usar
    `((k, g) for k, g in df.groupby(...))`.
  - Validado nos testes (804 Ida+Volta, 821 Circular) e na execução completa:
    23 abas, 1.281 partidas (tabela reduzida do dia), gate OK.

---

## 2026-10-15 — Script 1.3: QH factíveis a partir de tabela de contagens (partidas_pf_rio)

- Criado `codigos_py/1.3_qh_a_partir_de_partidas.py` (evolução do plano
  `PLANO_1.3_qh_a_partir_de_partidas.md`, com mudanças combinadas com o usuário):
  - **Entrada:** tabela agregada (não lista de partidas) — colunas por nome,
    tolerantes a acento/caixa (`Serviço`, `Vista`, `Sentido`, `Faixa`,
    `Partidas_Faixa`); utf-8 com fallback latin-1. `-` em contagens → 0
    (config `traco_ausente`: `zerar`|`erro`). Valida faixas padrão, domínio de
    sentidos, duplicatas e vista única por grupo.
  - **`trip_headsign`:** Ida → 2ª parte da vista (`Origem - Destino`); Volta →
    1ª parte; Circular → literal `Circular`. Validado contra `trips.txt` do GTFS
    (38/38 grupos Ida/Volta batem). Vista sem exatamente 2 partes em grupo com
    partidas → aborta.
  - **Bandas:** por faixa com n>0, `h = (dur//n // g)*g` (g=300 default, se 0 usa
    `dur//n`), `start = início da faixa`, `end = start + n*h` — contagem exata,
    sem vazamento. 1 banda/faixa, sem fusão.
  - **Saída:** `horarios_{servico}_{headsign}_{service_id}.csv` (default
    `F_REG`), campos idênticos ao script 1 (`trip_id` vazio). Pasta:
    `qh_por_linha_partidas/{estudo}Q`. Relatórios `relatorio_bandas.csv` +
    `_resumo.txt`. Gate duro antes de gravar (reexpansão = entrada, sem vazamento,
    headway múltiplo de g, in = out).
  - **Validado com `partidas_pf_rio.csv` (versão ampliada de 2026-10-15:**
    7.556 linhas, 448 serviços, 839 grupos, 23.971 partidas): **752 arquivos,
    5.714 bandas, 0 divergências** na reexpansão independente. 87 grupos pulados
    (contagens todas `-`/zero). Colisões de headsign: 0.
  - Pendências futuras (fora do escopo desta entrega): aba Streamlit, seção no
    README, entrada no CHANGELOG; registro do script no AGENTS.md.

---

## 2026-10-06 — Extração dos validadores para o projeto irmão `validacao`

- **Decisão do usuário:** mover o código `0` e a pasta `validacao/` para um novo
  projeto em `C:\github_repositories\validacao` (layout achatado, sem subpasta) e
  **remover por completo** a aba 0 do Streamlit (sem apontar para caminho externo).
- Saíram daqui: `codigos_py/0_validar_gtfs_entrada.py`,
  `src/tabs/tab_0_validar.py` (+ pyc), a entrada `"0. Validar"` e o bloco
  `with tabs[0]` de `src/app.py`, a seção `## 0️⃣` do `README.md` e o nó `A0` do
  diagrama mermaid. **Todos os índices `tabs[N]` seguintes foram decrescidos de 1**
  (erro clássico — são posicionais).
- Saiu também a pasta `validacao/` (script `validar_gtfs.py`, `README.md`,
  `CHANGELOG.md`, CSVs de exemplo e zip de 32 MB).
- Ajustes no novo projeto: `validar_gtfs.py` (`GTFS_PATH`/`OS_PATH`/`OUTPUT_DIR`
  hardcoded agora apontam para `C:\github_repositories\validacao`; docstring sem o
  prefixo `validacao/`), `README.md` reescrito cobrindo os dois scripts (a seção do
  script 0 foi **transportada** do README daqui, não apagada) e `CHANGELOG.md`
  ganhou `[2.0.0]`.
- `CHANGELOG.md` daqui: a entrada `### Adicionado` de 2026-10-06 (módulo
  `validacao/`) foi substituída por `### Removido` — o módulo não existe mais neste
  repositório e documentação sua passa a viver no projeto irmão.
- O script 0 é portátil: só lê caminhos via `--config`/hardcodes absolutos
  (`C:/R_SMTR/...`), sem dependência de `codigos_py/` nem de `__file__`.
- `src/implementation_plan.md` e `src/task.md` **não** foram alterados: são
  registros históricos de um plano concluído. `src/walkthrough.md` foi atualizado
  (10 → 9 scripts).

---

## 2026-10-01 — Investigação OS 184 (encerrada) e plano do script 1.3

### Investigação: OS 184 × GTFS 0164 (encerrada, sem alterações no GTFS)

- Reclamação: a OS regular de domingo gera >2 trips por serviço/faixa/shape.
- Achado: a **fragmentação vem do GTFS de origem** (`gtfs_combi_2029-10-01Q.zip`),
  não do pipeline. 278 células violando, das quais **168 são fragmentação pura**
  (`gtfs == plano`, 91 serviços) e 80 são falta de oferta em GTU/TUSE (−724 partidas).
- Consórcios: Internorte 57, Santa Cruz 51, Transcarioca 39, Intersul 31, GTU 61,
  TUSE 21, fora do plano 18.
- **Diretriz do usuário:** diferenças de plano > GTFS nas linhas **fora de TUSE/GTU**
  são intencionais (linhas `SN*`). Confirmado: dentro das violações dos outros
  consórcios há **0 células** com `gtfs < plano`.
- Relatórios da investigação ficaram na raiz e foram adicionados ao `.gitignore`
  (`celulas_fragmentacao_domingo.csv`, `relatorio_plano184_vs_gtfs0164_domingo*.csv`).
- **Abordagem descartada:** remontar o GTFS a partir da lista de partidas (exigiria
  reference GTFS para offsets/shapes/calendar; o usuário aconsidered complexa e
  ruidosa). O plano também exigia decidir a tolerância de headway.

### Decisão: gerar QH a partir da lista de partidas (script `1.3`)

- Escopo: `quadros_dom_04-10.csv` (saída do 7.2) → QH no formato do script 1.
- **Invariante definido pelo usuário:** o número de partidas por faixa é o invariante;
  o headway é regulado para preservá-lo. `end = start + n·h` garante exatamente `n`.
- **Duas armadilhas encontradas nos dados:**
  1. A coluna `faixa` usa `hora % 24` (875 partidas com hora ≥ 24, até 28:00), então 6
     faixas ficam não-contíguas e o headway fica negativo. Chave deve incluir
     `ciclo = segundos // 86400`.
  2. Sem clamp de faixa, 1.186 células vazam para a faixa seguinte e a contagem muda.
     Com `h = min(h, max(disponivel // n, 1))`: 0 vazamento.
- **Dano na contagem não depende do nº de bandas** — depende do clamp. 1, 2 e 3
  bandas por faixa têm dano zero; o desempate é fidelidade × volume.
- Resultado medido (1 banda/faixa): **6.557** bandas (contra 18.783 do 0164, −65%),
  **100% das 41.291 partidas preservadas**, 0 vazamento, desvio mediano 0 s,
  médio 212 s, máx 48 min, 1 trip por faixa (limite do validador: 2).
- Plano completo em `PLANO_1.3_qh_a_partir_de_partidas.md` (passos, parâmetros,
  linha de base e riscos). `AGENTS.md` e `.gitignore` atualizados.

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
- Script `0_validar_gtfs_entrada` (agora em `C:\github_repositories\validacao`) faz
  validações de padrão de `trip_headsign` (excepcionalidades `[...]`) e retorna
  exit code específico.
- Script `5_juntar_gtfs` cuida da versão pública `gtfs_rio-de-janeiro_pub.zip` e
  interna `gtfs_combi_YYYY-MM-QQ.zip`; variantes 5.1/5.2/5.3/5.4 cobrem casos
  específicos (modal único, concatenação simples, substituição de linhas,
  eliminação de duplicatas preservando EXCEP).
- Seqüência histórica de refatoração: pipeline original em R foi portado para
  Python; a interface Streamlit veio depois (com abas por script).
- Pontos de atenção: `Iniciar_App.bat` inicializa a aplicação; `stop_times.csv`
  na raiz é dado de trabalho, não código.
### 2026-10-06 — Script de Validação Pós-Pipeline (validacao/validar_gtfs.py)
- Criada pasta alidacao/ com script alidar_gtfs.py e documentação README.md.
- Implementado conjunto completo de verificações pós-processamento:
  1. Conformidade de arquivos e colunas GTFS padrão (agency, feed_info, calendar, routes, trips, etc.).
  2. Integridade referencial: trips com stop_times, frequencies, route_id e shape_id válidos, sem registros órfãos.
  3. Regras de calendário e itinerários alternativos: service_id == EXCEP estritamente com [...] no headsign.
  4. Extensões de trajeto: coerência stop_times vs shapes (tolerância 5%) e campos de distância preenchidos.
  5. Anomalias de shape_id: identificação de notação científica (+).
  6. Padrão de cabeçalho da OS: suporte a formato por sentido e formato por colunas de ida/volta.
  7. Cruzamento OS × GTFS: linhas faltantes, linhas alternativas, divergência de extensões.
- Saída: CSV delimitado por ; e decimal , (compatível com Google Sheets), consolidando status e contagem de afetados.
- Ajuste no check 2.3 de frequencies: trips com service_id == EXCEP não exigem frequencies (regra de negócio).
- Ajuste no check 2.3: aceita viagens regulares modeladas como timetable (com horários definidos em stop_times.txt sem frequencies.txt, como na linha 899/2613/2614).
- Ajuste no check 3.2: viagens com service_id == EXCEP aceitam linhas do padrão TP (4 dígitos seguidos de TP, ex: 2308TP), além do padrão [evento] no headsign.

---

## 2026-10-19 — Quadros de ponto facultativo a partir do GTFS (1.4)

- Criado `codigos_py/1.4_qh_pf_a_partir_do_gtfs.py`: gera quadros `F_REG` direto do
  `frequencies.txt` de um GTFS (default `0171_gtfs_out_26_1E_ret.zip` na raiz),
  no mesmo formato de saída do script 1/1.3.
- Regras combinadas com o usuário:
  - Excluir agência MOBI-Rio (`20001`) **inteira** (qualquer route_type);
  - Filtrar globalmente `route_type=700` (exclui BRT 702 e Metrô 200);
  - Base de partidas: DU (`U_REG`) p/ Internorte `22003`, Intersul `22002`,
    Transcarioca `22004`, Santa Cruz `22005`; sábado (`S_REG`) p/ GTU `A2` e TUSE `B2`
    (`mapa_base` configurável);
  - Pasta de saída própria `qh_por_linha_pf_gtfs/{estudo}Q/` (não mistura com o 1.3);
    sem aba Streamlit (CLI/`--config`).
- Agrupa bandas por `(trip_short_name, trip_headsign)`; gate antes de gravar
  (bandas preservadas entrada×saída, `n=ceil((end−start)/headway)≥1`, total in=out).
- Execução real: 9.519 bandas → **804 quadros**, 40.744 partidas, gate OK;
  Excel 429 abas. Rotas sem bandas na base esperada (aviso): `SP766`, `899`,
  `SV899`, `LECD126`. Amostras conferidas (249 e 821) batem com o GTFS.
- Documentação: nova seção 1.4 no `README.md` e entrada em `AGENTS.md`.
