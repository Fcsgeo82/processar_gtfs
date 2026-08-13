# Tarefas — Aplicação Streamlit Pipeline GTFS

## Fase 1 — Infraestrutura
- [x] Atualizar `requirements.txt` com streamlit
- [x] Instalar streamlit no `.venv`
- [x] Criar `src/runner.py` (wrapper de subprocess)
- [x] Criar `src/tabs/__init__.py`

## Fase 2 — Adaptação dos Scripts (--config)
- [x] Adicionar suporte `--config` ao script 0
- [x] Adicionar suporte `--config` ao script 1
- [x] Adicionar suporte `--config` ao script 2
- [x] Adicionar suporte `--config` ao script 4
- [x] Adicionar suporte `--config` ao script 5
- [x] Adicionar suporte `--config` ao script 5.1
- [x] Adicionar suporte `--config` ao script 5.2
- [x] Adicionar suporte `--config` ao script 5.3
- [x] Adicionar suporte `--config` ao script 6
- [x] Adicionar suporte `--config` ao script 7
- [x] Adicionar suporte `--config` ao script 8
- [x] Adicionar suporte `--config` ao script 8.1
- [x] Adicionar suporte `--config` ao script 9
- [x] Adicionar suporte `--config` ao script 10

## Fase 3 — Aplicação Streamlit
- [x] Criar `src/app.py` (entrada principal + sidebar + abas)
- [x] Criar `src/tabs/tab_0_validar.py`
- [x] Criar `src/tabs/tab_1_extrair_qh.py`
- [x] Criar `src/tabs/tab_2_ajustar_st.py`
- [x] Criar `src/tabs/tab_4_trajetos.py`
- [x] Criar `src/tabs/tab_5_juntar.py` (agrupado: 5, 5.1, 5.2, 5.3)
- [x] Criar `src/tabs/tab_6_shapes.py`
- [x] Criar `src/tabs/tab_7_partidas.py`
- [x] Criar `src/tabs/tab_8_extensoes.py` (agrupado: 8, 8.1)
- [x] Criar `src/tabs/tab_9_filtrar.py`
- [x] Criar `src/tabs/tab_10_juntar_dois.py`

## Fase 4 — Verificação
- [x] Testar execução do Streamlit (`streamlit run src/app.py`)
- [x] Revisar se todos os 10 scripts principais estão cobertos
- [x] Atualizar a documentação do projetol
