# CONTEXTO — Sessão de Desenvolvimento 2026-08-04

## Resumo

Nesta sessão foram criados dois novos scripts Python ao pipeline de processamento de GTFS do projeto `processar_gtfs`, além da atualização da documentação.

---

## Scripts Criados

### `9_filtrar_gtfs_por_lista.py`

**Motivação:** A equipe recebeu uma lista de excepcionalidades/desvios (Serviço, Vista, Consórcio, Sentido, Extensão, Evento) e precisava gerar um GTFS contendo **apenas** as trips correspondentes àquela lista, eliminando todo o restante do GTFS de forma consistente (stop_times, shapes, stops, calendar, etc.).

**Decisões de design:**

- A correspondência é feita por **chave composta de 5 campos** (excluindo Extensão, que é apenas referência):
  - `Serviço` → `trips.trip_short_name`
  - `Vista` → `routes.route_long_name`
  - `Consórcio` → `agency.agency_name`
  - `Sentido` → `trips.direction_id` (Ida=0, Volta=1)
  - `Evento` → texto entre `[...]` extraído do `trips.trip_headsign`
- A lista de filtro é embutida no próprio script como string TSV na constante `LISTA_FILTRO_RAW`, facilitando o versionamento e rastreabilidade das excepcionalidades.
- O filtro de calendário (`CALENDARIOS_ALVO`) é aplicado antes do cruzamento, reduzindo o espaço de busca. Padrão: `["EXCEP"]`.
- O script reporta explicitamente quais entradas da lista **não tiveram match** no GTFS — útil para detectar discrepâncias entre a lista recebida e o GTFS disponível.
- Usa a função `clean_gtfs` (mesma lógica do `5_juntar_gtfs.py`) para propagar a remoção em cascata a todas as tabelas associadas.

**Entradas:**
- `sppo_YYYY-MM-QQQ_PROC.zip`
- Lista de excepcionalidades embutida no script

**Saída:**
- `sppo_YYYY-MM-QQQ_FILTRADO.zip`

---

### `10_juntar_dois_gtfs.py`

**Motivação:** Com o GTFS filtrado em mãos, precisava-se combiná-lo com outro GTFS (geralmente o GTFS completo processado), resultando em um GTFS unificado sem duplicações entre as tabelas.

**Decisões de design:**

- A estratégia de deduplicação opera em **dois níveis** por tabela:
  1. **Linha inteira:** remove registros 100% idênticos.
  2. **Chave primária:** em caso de conflito (mesma chave, dados diferentes), prevalece sempre o **GTFS_PRINCIPAL** (configurável). Isso permite que os trajetos alternativos corretos do GTFS filtrado não sejam sobrescritos pelos registros do GTFS base.
- As chaves primárias por tabela são declaradas explicitamente no dicionário `CHAVES_PRIMARIAS`, tornando a lógica transparente e fácil de ajustar.
- A tabela `feed_info` não tem chave primária útil; o script mantém apenas o registro do PRINCIPAL.
- Após a junção, `clean_gtfs` é aplicado para garantir integridade referencial.
- O log informa exatamente quantas duplicatas foram removidas por tabela (exatas vs. conflitos de chave).

**Entradas:**
- `GTFS_PRINCIPAL`: `sppo_YYYY-MM-QQQ_FILTRADO.zip` (tem precedência)
- `GTFS_SECUNDARIO`: `sppo_YYYY-MM-QQQ_PROC.zip` (GTFS base)

**Saída:**
- `sppo_YYYY-MM-QQQ_COMBINADO.zip`

---

## Fluxo dos Novos Scripts

```
Lista de Excepcionalidades (TSV)
         │
         ▼
sppo_PROC.zip ──► [9_filtrar_gtfs_por_lista.py] ──► sppo_FILTRADO.zip
                                                              │
sppo_PROC.zip ────────────────────────────────────────────── ┤
                                                              ▼
                                              [10_juntar_dois_gtfs.py]
                                                              │
                                                              ▼
                                                   sppo_COMBINADO.zip
```

---

## Padrões Mantidos

Ambos os scripts seguem os padrões já estabelecidos no projeto:

| Padrão | Adotado em |
|--------|-----------|
| `BASE_DADOS = Path("C:/R_SMTR/dados")` + `sufixo` | Configurações no topo do arquivo |
| `def log_msg(msg)` com timestamp | Log consistente com os demais scripts |
| `def read_gtfs(zip_path)` | Leitura padrão de GTFS ZIP |
| `def write_gtfs(gtfs_dict, zip_path)` com `ZIP_STORED` | Escrita sem compressão (evita erro zlib em arquivos grandes) |
| `def clean_gtfs(gtfs_dict)` | Limpeza em cascata equivalente ao `gtfstools::filter_by_trip_id` do R |
| `sys.stdout.reconfigure(encoding='utf-8')` | Encoding correto no Windows |

---

## Documentação Atualizada

- **`README.md`**: adicionadas seções `9️⃣` e `1️⃣0️⃣` com tabela de descrição completa; diagrama Mermaid atualizado com o sub-fluxo de filtragem e junção em vermelho (`#c0392b`).

---

## Lista de Excepcionalidades Utilizada (2026-08-04)

A lista embutida no script 9 contém **63 entradas** cobrindo os seguintes serviços:

`104`, `107`, `133`, `161`, `167`, `169`, `201`, `202`, `249`, `361`, `371`, `410`, `426`, `553`, `624`, `665`, `838`, `910`, `913`, `917`, `919`, `920`, `961`, `LECD131`, `LECD147`, `LECD151`, `SN232`, `SN265`, `SN624`, `SV624`, `SV917`, `SVB665`

Consórcios envolvidos: **Intersul**, **Internorte**, **Transcarioca**, **Santa Cruz**

Tipos de evento: `[desvio_feira]`, `[desvio_obras]`, `[desvio_tunel]`, `[desvio_aterro]`, `[desvio_lazer]`, `[desvio_maracana]`, `[desvio_maracana_2]`, `[desvio_tunel_e_desvio_aterro]`, `[desvio_maracana_e_tunel]`, `[excepcionalidade]`, `[excepcionalidade_1]`, `[excepcionalidade_2]`, `[eventos_climaticos]`, `[eventos_climaticos_1]`
