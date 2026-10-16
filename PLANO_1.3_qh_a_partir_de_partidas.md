# Plano — `1.3` gerar quadros de horário a partir da lista de partidas

> **EXECUTADO em 2026-10-15** — ver `codigos_py/1.3_qh_a_partir_de_partidas.py`.
> Plano adaptado na execução: entrada = tabela de contagens agregada (formatos
> **wide** com uma coluna por faixa e **longo** Faixa+Partidas) em vez da lista
> bruta de partidas do 7/7.2; acrescentada exportação **Excel** (uma aba por
> linha). Este documento fica como registro do desenho original.
> **Status:** pronto para execução em 2026-10-02 (elaborado em 2026-10-01)
> **Origem:** script `7` → `7.2` produzem a lista de partidas; falta o elo de volta para QH.
> **Arquivos de referência:** `codigos_py/1_extrair_qh_especificado_no_gtfs.py` (formato de saída),
> `codigos_py/1.1_extrair_qh_partidas.py` (inverso deste), `codigos_py/1.2_combinar_quadros_horarios.py` (consumidor).

---

## 1. Objetivo

Gerar os quadros de horário no **formato do script 1** (`horarios_{servico}_{vista}_{calendario}.csv`)
a partir de um **arquivo de partidas** (saída do `7`/`7.2`), sem ler GTFS.

```
7 (lista) ──► partidas.csv ──► 1.3 (novo) ──► horarios_{linha}_{vista}_{servico}.csv ──► 1.2 ──► GTFS
```

**Por quê:** a OS especial de 04/10/2026 (1º turno) gera mais de duas trips para o mesmo
serviço/faixa/shape. A fragmentação nasce no GTFS de origem (`gtfs_combi_2029-10-01Q.zip`),
não no pipeline. Consolidar as bandas **no nível do quadro de horário** resolve a causa,
antes de qualquer montagem de GTFS.

### Contexto medido (ver `CONTEXTO.md` / investigação da OS 184)

| Verificação | Valor |
|---|---|
| Células `(serviço, faixa, shape)` com mais de 2 trips no domingo | 278 |
| destas, com `gtfs == plano` (fragmentação pura) | 168 (91 serviços) |
| Bandas em `0164_gtfs_out_26_1E.zip` → `frequencies.txt` | 18.783 |
| Bandas producidas por este plano | **6.557** (−65%) |
| Trips por `(serviço, faixa, shape)` no output | **1** (limite do validador: 2) ✅ |

---

## 2. Requisito invariante

> **O número de partidas por faixa é o invariante. O headway é o que se regula para preservá-lo.**

Uma banda de frequência com `start_time`, `end_time` e `headway_secs` expande para
`{ start + k·h  :  k ≥ 0,  start + k·h < end }`. Logo, se

```
end_time = start_time + n × headway      (n = número de partidas da célula)
```

a expansão devolve **exatamente `n` partidas**, para qualquer `h ≥ 1`.

**Consequência: a contagem nunca é danificada — desde que a banda não atravesse a fronteira da faixa.**
As duas subseções seguintes tratam exatamente disso.

---

## 3. Duas armadilhas nos dados (obrigatórias no algoritmo)

### 3.1 A coluna `faixa` dá a volta em 24h

O script `7` (`7_lista_partidas.py:243-261`) calcula a faixa com `horas = total_horas % 24`.
No arquivo `quadros_dom_04-10.csv`:

- **875 partidas com hora ≥ 24** (todas `dom`, até `28:00:00`);
- por isso **6 faixas ficam não-contíguas** — a faixa `00:00-01:00` contém partidas de 00h **e** de 24h;
- agrupando só por faixa, `t_n − t_1` fica enorme ou negativo e o headway sai **negativo**
  (medido: −230 min, −276 min, −345 min).

**Correção:** a chave da célula passa a ser
`(tipo_dia, linha, headsign, ciclo, faixa)`, com `ciclo = segundos // 86400`.
Sem isso o output é inutilizável.

> A coluna `faixa` do arquivo de entrada está **100% consistente** com `departure_time`
> (0 divergências em 41.291 linhas) — o problema é exclusivamente a não-contiguidade do
> agrupamento, não um erro de rotulagem.

### 3.2 A banda pode vazar para a faixa vizinha

Se `start` está no fim da faixa, `end = start + n·h` ultrapassa a fronteira e a contagem
da faixa seguinte muda — que é exatamente o dano inaceitável.

**Correção:** limitar o headway ao espaço disponível dentro da faixa:

```
h = min(h_inicial, max(disponivel_na_faixa // n, 1))
```

Medido: **0 células vazando, 0 partidas migradas** com clamp; **1.186 células e 1.186
partidas migrando** sem clamp (2,9% do total).

---

## 4. Algoritmo

Para cada arquivo `(trip_short_name, trip_headsign, service_id)`:
para cada célula `(ciclo, faixa)` com `n` partidas `t₁ … tₙ` (ordenadas):

```
disponivel = (ciclo × 86400 + fim_da_faixa) − t₁

se n == 1:
    h_inicial = headway_minimo                    # padrão 60 s
senão:
    h_inicial = max(round((tₙ − t₁) / (n − 1)), 1)

h  = min(h_inicial, max(disponivel // n, 1))

start_time = t₁
end_time   = t₁ + n × h          # ← garante exatamente n partidas
headway_secs = h
```

Saída de cada arquivo, ordenada por `start_time`:

```
trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs
,Central do Brasil,007,04:50:00,05:00:00,60
```

`trip_id` em branco (igual ao script 1, linha 95).

### Faixas (14, padrão do projeto — igual ao script 7 e ao 7.1)

```
00-01  01-02  02-03  03-04  04-05  05-06
06-09  09-12  12-15  15-18  18-21
21-22  22-23  23-24
```

Os limites de cada faixa são calculados **relativos ao ciclo**:
`inicio = ciclo × 86400 + h_ini × 3600`, `fim = ciclo × 86400 + h_fim × 3600`.

### Parâmetro `max_bandas_por_faixa`

Implementar com default **1**. Medido: o dano na contagem é **zero para 1, 2 e 3 bandas**
(o clamp é aplicado por sub-banda), então o parâmetro é gratuito em termos de contagem
e existe só como margen:

| Bandas/faixa | Total de bandas | Desvio mediano | Desvio médio | Desvio máx | Trips/faixa |
|---|---|---|---|---|---|
| **1 (default)** | **6.557** | 0 s | 212 s | 48 min | 1 ✅ |
| 2 | 10.798 | 0 s | 74 s | 27 min | 2 ✅ |
| 3 | 14.184 | 0 s | 34 s | 20 min | 3 ❌ |

---

## 5. Especificação do script

**Arquivo:** `codigos_py/1.3_qh_a_partir_de_partidas.py`

**Entrada:** CSV no formato do script 7 / 7.2. Colunas usadas:
`trip_short_name`, `trip_headsign`, `departure_time`, `tipo_dia`.
Colunas `direction_id`, `faixa`, `agency_name`, `extensao`, `route_type`, `intervalo` são ignoradas.

**Saída:** um CSV por combinação `(trip_short_name, trip_headsign, service_id)`,
em pasta separada para o `1.2` consumir via `pasta_entrada`:

```
BASE_RESULTADOS/quadro_horario_extraido/{ano}/{mes}/qh_por_linha_partidas/{estudo}Q/
horarios_{servico}_{vista}_{calendario}.csv
```

### Parâmetros (`--config <json>`, mesma convenção do resto do projeto)

| Chave | Default | Descrição |
|---|---|---|
| `caminho_partidas` | — (obrigatório) | Caminho do CSV de partidas |
| `BASE_RESULTADOS` | `C:/R_SMTR/resultados` | Base das pastas de saída |
| `ano_gtfs` / `mes_gtfs` / `estudo_gtfs` | `2029` / `10` / `01` | Montagem do caminho de saída |
| `pasta_saida` | derivado acima | Sobrescreve a pasta de saída |
| `servico_por_tipo_dia` | `{"du":"U_REG","sab":"S_REG","dom":"D_REG"}` | Mapa tipo de dia → `service_id` |
| `headway_minimo` | `60` | Headway para células com uma única partida |
| `max_bandas_por_faixa` | `1` | Ver seção 4 |
| `linhas_rodar` | todas | Filtro de `trip_short_name` |
| `validar_faixa_entrada` | `true` | Aborta se a coluna `faixa` divergir do horário |
| `tipo_dia_desconhecido` | `"erro"` | `erro` ou `ignorar` |
| `limite_relatorio` | `600` | Desvio (s) acima do qual a célula entra no relatório de desvios |
| `gerar_relatorio` | `true` | Grava os dois relatórios |

### Restrições de compatibilidade com o `1.2`

- Só emitir `service_id` da lista `{U, S, D, U_REG, S_REG, D_REG}`; o `parse_filename`
  do `1.2` (linha 106) só reconhece esses.
- Reusar `sanitize_filename` do `1.1` (substitui `\ / : * ? " < > |` e normaliza espaços).
  Acentos e espaços nos letreiros são preservados — o `1.2` os parseia sem problema.
  **Verificado:** 0 colisões de nome e 1.284/1.284 nomes reconhecidos pelo `1.2`.

### Relatórios na pasta de saída

| Arquivo | Conteúdo |
|---|---|
| `relatorio_bandas.csv` | arquivo, ciclo, faixa, `n_partidas`, `headway_secs`, `start_time`, `end_time`, `n_bandas`, `desvio_max_seg` |
| `celulas_desvio_alto.csv` | só as células com `desvio_max_seg > limite_relatorio` |
| `_resumo.txt` | totais: arquivos, células, bandas, partidas de entrada, partidas de saída |

---

## 6. Verificação (gate antes/depois de gravar)

Reexpandir as bandas geradas e comparar com a lista de entrada:

1. **Contagem idêntica** por `(arquivo, ciclo, faixa)` — gate duro, aborta se falhar.
2. Nenhuma banda com `end_time` além do fim da sua faixa.
3. `headway_secs ≥ 1` e `end_time > start_time` em todas as linhas.
4. Soma das partidas de saída = soma das partidas de entrada.

O script deve imprimir esse relatório no console (o `run_script` já faz log em tempo real).

---

## 7. Passos de execução

- [ ] **1.** Criar `codigos_py/1.3_qh_a_partir_de_partidas.py`
      (reusar `sanitize_filename` do `1.1` e `horario_to_seconds` / `seconds_to_horario` do `1.2`).
- [ ] **2.** Implementar leitura + validação (`validar_faixa_entrada`) + normalização de tempo.
- [ ] **3.** Implementar o agrupamento com chave `(…, ciclo, faixa)` — **não agrupar só por `faixa`**.
- [ ] **4.** Implementar o ajuste de bandas com o clamp de faixa.
- [ ] **5.** Implementar a gravação dos CSVs + `relatorio_bandas.csv` + `celulas_desvio_alto.csv` + `_resumo.txt`.
- [ ] **6.** Implementar o gate de verificação e rodá-lo com `quadros_dom_04-10.csv`.
- [ ] **7.** Conferir os números contra a linha de base da seção 8.
- [ ] **8.** Testar o consumo: rodar o `1.2` com `pasta_entrada` apontando para a pasta nova,
      em uma linha de teste (ex.: `378`), e confirmar que ele lê os arquivos e combina faixas.
- [ ] **9.** Criar `src/tabs/tab_1_3_qh_partidas.py` (modelar em `src/tabs/tab_1_extrair_qh.py`).
- [ ] **10.** Registrar a aba em `src/app.py`: adicionar `"1.3 QH de Partidas"` à lista de
      `st.tabs` (após `"1. Extrair QH"`) e o `with tabs[N]: tab_1_3_qh_partidas.render()`
      na posição correspondente — **atenção ao índice**, todos os `with tabs[...]` são posicionais.
- [ ] **11.** Documentar: nova seção `## 1️⃣.3️⃣` no `README.md` (formato da tabela de
      `1.1`/`1.2`) e menção em "Visão Geral do Pipeline" (linha ~404).
- [ ] **12.** Entrada em `CHANGELOG.md` na seção `[Não lançado] → Adicionado`.
- [ ] **13.** Atualizar `AGENTS.md` (estrutura: `codigos_py/` numerado, `src/tabs/tab_*.py`).

---

## 8. Linha de base para conferir (medido em 2026-10-01)

Entrada: `quadros_dom_04-10.csv` — 41.291 linhas, 10 colunas
(`6.192` `dom` + `35.099` `du`).

| Métrica | Esperado |
|---|---|
| Arquivos gerados | **1.284** |
| Células `(ciclo, faixa)` | **6.557** |
| Bandas geradas (`max_bandas=1`) | **6.557** |
| Partidas de entrada / saída | **41.291 / 41.291** (100%) |
| Células com `n = 1` | 2.316 |
| Bandas que vazam da faixa | **0** |
| Headway `< 1` | **0** |
| Desvio mediano / médio | 0 s / 212 s |
| Desvio máximo | 48 min (`du SV908 Bonsucesso 15-18`, 5 partidas) |
| Células com desvio ≤ 1 min | 67,8% |
| Células com desvio ≤ 15 min | 94,3% |

Piores células esperadas (para conferência):

| tipo_dia | linha | letreiro | faixa | n | desvio |
|---|---|---|---|---|---|
| du | SV908 | Bonsucesso | 15-18 | 5 | 48,0 min |
| du | 518 | Circular | 12-15 | 3 | 40,0 min |
| du | 901 | Bonsucesso | 12-15 | 3 | 40,0 min |
| du | 940 | Madureira | 06-09 | 10 | 40,0 min |
| du | 650 | Engenho Novo | 06-09 | 18 | 38,8 min |

---

## 9. Pendências e riscos

1. **O que o `1.3` resolve:** a contagem e a regularização do quadro. **O que ele não
   resolve:** as células com desvio alto (cauda). Se os 48 min de pior caso incomodarem,
   subir `max_bandas_por_faixa` para 2 (dano zero na contagem, ainda dentro do limite do
   validador, mas dobra as bandas).
2. **Montar o GTFS a partir desses quadros** é etapa seguinte e continua em aberto — o
   escopo deste plano é só gerar os QH.
3. **GTU/TUSE com oferta reduced** (80 células, −724 partidas no domingo) foi identificado
   na investigação e **não é tratado por este plano**. É um problema de oferta, não de
   fragmentação.
4. As 875 partidas com hora ≥ 24 produzem `start_time`/`end_time` acima de `24:00:00`,
   o que é legal em GTFS, mas **deve ser conferido** pelo consumidor do quadro.
5. `linhas_excluir` e `trip_id_fantasma` do script 7 não se aplicam aqui: o `1.3` consome
   a lista já filtrada. As 218 chaves `(linha, sentido)` que existem no GTFS e não estão na
   lista simplesmente não aparecerão no output — comportamento esperado.

---

## 10. Referências

| Arquivo | Papel |
|---|---|
| `codigos_py/1_extrair_qh_especificado_no_gtfs.py` | Formato de saída e nomenclatura de arquivo |
| `codigos_py/1.1_extrair_qh_partidas.py` | `sanitize_filename`, grupo de colunas, padrão de log |
| `codigos_py/1.2_combinar_quadros_horarios.py` | `horario_to_seconds`, `seconds_to_horario`, `parse_filename` (consumidor) |
| `codigos_py/7_lista_partidas.py` | Origem do arquivo de partidas; definição das 14 faixas (linha 243) |
| `codigos_py/7.2_combinador_partidas.py` | Produz `quadros_dom_04-10.csv` |
| `src/tabs/tab_1_extrair_qh.py` | Modelo para a nova aba |
| `src/app.py` | Registro das abas (índices posicionais) |
| `9_filtrar_gtfs_por_lista.py` | `clean_gtfs()` em cascata, se a etapa de montagem de GTFS precisar |
