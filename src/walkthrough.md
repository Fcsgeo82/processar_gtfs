# Aplicação do Pipeline GTFS em Streamlit

O pipeline de processamento do GTFS foi completamente refatorado para suportar uma interface de usuário amigável via Streamlit.

## O que foi feito:

1. **Retrocompatibilidade e CLI**:
   - Todos os 10 scripts principais (`0_validar_gtfs_entrada.py` a `10_juntar_dois_gtfs.py`) foram adaptados.
   - Os scripts agora possuem suporte a argumentos via linha de comando (CLI) através da biblioteca `argparse`.
   - Utilizam a _flag_ `--config` para carregar um dicionário JSON com as configurações (ex: caminhos, ano, mês, quinzena/estudo).
   - A lógica original se mantém: se a flag não for fornecida, os scripts utilizam as variáveis globais _hardcoded_ que existiam anteriormente.

2. **Interface Streamlit**:
   - A aplicação principal está localizada em `src/app.py`.
   - Utilizamos o módulo `src/runner.py` para isolar a execução. Ao clicar em executar em qualquer script na interface, o runner cria um `subprocess.Popen` que executa o script nativo em modo shell em paralelo, capturando sua saída padronizada (stdout e stderr) em tempo real e exibindo na interface.
   - Foram implementados os requisitos adicionais solicitados:
     - **Agrupamento**: Os scripts `5*` e `8*` foram agrupados nas suas abas correspondentes (Abas 5 e 8).
     - **Inputs**: Text inputs preenchidos por variáveis globais localizados na Sidebar, e botões de Upload (`file_uploader`) habilitados quando há carga alternativa de arquivos.
     - **Tooltips**: Adicionados `help="..."` em todos os campos explicando sua função.

## Como Executar a Interface

Para rodar a aplicação construída:

```bash
# Na raiz do projeto processar_gtfs
python -m streamlit run src/app.py
```

A aplicação está rodando atualmente e já pode ser testada!
