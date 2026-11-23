# Tarefa: Reestruturação da documentação técnica do projeto Python

Atue como um **Senior Python Engineer, Software Architect e Technical Writer**, especialista em documentação de projetos Python, arquitetura de pipelines de dados, engenharia de software e boas práticas de desenvolvimento.

Sua tarefa é analisar e reestruturar a documentação deste projeto, adotando uma arquitetura documental de dois níveis:

1. **README.md:** documentação principal, concisa e introdutória, funcionando como porta de entrada do projeto.
2. **docs/:** documentação técnica complementar, detalhada e organizada por assunto, permitindo consultar a arquitetura, o pipeline, os scripts e as configurações sem sobrecarregar o README.

O objetivo é produzir uma documentação profissional, clara, consistente, pesquisável e de fácil manutenção.

Qualquer desenvolvedor que tenha contato com o projeto deverá conseguir compreender rapidamente sua finalidade, identificar os componentes, localizar scripts, entender suas dependências e executar corretamente o pipeline.

---

# 1. Análise prévia obrigatória

Antes de modificar qualquer arquivo:

1. Examine a estrutura completa do repositório.
2. Leia os arquivos de configuração e gerenciamento de dependências (`pyproject.toml`, `requirements.txt`, `setup.cfg`, `environment.yml` ou equivalentes).
3. Analise os scripts Python, módulos, pacotes e arquivos auxiliares.
4. Identifique os pontos de entrada (*entry points*) e os comandos utilizados para executar o sistema.
5. Identifique a sequência de processamento e as dependências entre os scripts.
6. Examine os arquivos de documentação existentes.
7. Identifique configurações, variáveis de ambiente, parâmetros, diretórios de entrada e saída e integrações externas.
8. Verifique instruções de desenvolvimento em arquivos como `AGENTS.md`, `CONTEXT.md` e documentos equivalentes.

Não presuma funcionalidades com base apenas nos nomes dos arquivos. Examine o código para compreender o comportamento real de cada componente.

Não invente comandos, parâmetros, caminhos, dependências ou funcionalidades.

Antes de começar, apresente um breve diagnóstico da documentação existente e um plano de reestruturação.

# 2. Arquitetura documental de dois níveis

## Nível 1 — README.md

O README deve funcionar como a página inicial do projeto e oferecer uma visão geral suficiente para que um novo desenvolvedor entenda o sistema e saiba por onde começar.

**Princípio fundamental: o README deve responder rapidamente o que é o projeto, para que serve, como configurá-lo e como executá-lo.**

Não transforme o README em um manual técnico extenso. Informações detalhadas devem ser direcionadas aos documentos específicos dentro de `docs/`.

Estrutura recomendada:

### 2.1. Identificação do projeto

- Nome do projeto.
- Descrição objetiva de sua finalidade.
- Problema que o sistema resolve.
- Principais funcionalidades.
- Tecnologias principais utilizadas.

### 2.2. Índice de navegação

Crie um sumário com links internos para as seções principais.

Inclua também uma seção de documentação com links relativos para os arquivos existentes em `docs/`.

### 2.3. Visão geral

Apresente resumidamente:
- Finalidade do sistema.
- Principais componentes.
- Funcionamento geral.
- Características relevantes da arquitetura.

### 2.4. Estrutura do projeto

Apresente uma árvore simplificada de diretórios, destacando os componentes mais importantes.

Explique brevemente a finalidade de cada diretório relevante.

Não reproduza uma árvore excessivamente detalhada.

### 2.5. Instalação e configuração

Apresente os procedimentos essenciais para:
- Preparar o ambiente Python.
- Criar e ativar o ambiente virtual.
- Instalar as dependências.
- Configurar requisitos externos.
- Preparar as configurações obrigatórias.

Utilize comandos reais e compatíveis com o projeto.

### 2.6. Execução rápida

Apresente um exemplo funcional de execução do projeto, com os comandos necessários para iniciar o processamento.

Diferencie, quando aplicável:
- Execução completa do pipeline.
- Execução de etapas específicas.
- Execução de funcionalidades independentes.

Direcione para `docs/pipeline.md` quando forem necessários detalhes adicionais.

### 2.7. Documentação técnica

Crie uma seção de navegação para os documentos complementares.

Apresente uma descrição curta de cada documento, facilitando a identificação do conteúdo procurado.

### 2.8. Testes e validação

Apresente os comandos essenciais para executar os testes e verificar a integridade do projeto.

### 2.9. Desenvolvimento e contribuição

Inclua orientações resumidas para manutenção e evolução do projeto, direcionando para a documentação detalhada quando necessário.

---

## Nível 2 — Documentação técnica em docs/

Crie uma estrutura de documentação complementar, organizada por responsabilidade.

Estrutura inicial recomendada:

    docs/
    ├── architecture.md
    ├── pipeline.md
    ├── scripts_reference.md
    ├── configuration.md
    ├── data_dictionary.md
    ├── testing.md
    └── troubleshooting.md

Adapte essa estrutura à complexidade real do projeto. Não crie documentos vazios ou redundantes.

Cada documento deverá ter uma finalidade clara.

### 2.10. architecture.md — Arquitetura do projeto

Documente:
- Organização geral do sistema.
- Responsabilidades dos módulos e pacotes.
- Componentes principais.
- Integrações externas.
- Fluxo de comunicação entre componentes.
- Decisões arquiteturais relevantes.
- Padrões de organização e nomenclatura.

Inclua diagramas Mermaid quando contribuírem para explicar a arquitetura.

### 2.11. pipeline.md — Fluxo de processamento

Esta é uma das documentações mais importantes.

Descreva detalhadamente o funcionamento do pipeline.

Para cada etapa, apresente:

| Informação | Descrição |
|---|---|
| Etapa | Identificação e posição no pipeline |
| Script | Arquivo responsável |
| Objetivo | Finalidade do processamento |
| Entradas | Dados e arquivos consumidos |
| Saídas | Resultados produzidos |
| Dependências | Etapas anteriores necessárias |
| Execução | Comando para iniciar a etapa |

Organize as etapas na ordem correta de execução.

Identifique claramente:
- Etapas obrigatórias.
- Etapas opcionais.
- Etapas independentes.
- Fluxos alternativos.
- Pontos de entrada.
- Dependências entre etapas.
- Possibilidade de reprocessamento.

Inclua um diagrama Mermaid representando o fluxo completo, com ramificações quando necessário.

O diagrama deve refletir o comportamento real do código.

### 2.12. scripts_reference.md — Catálogo de scripts

Este documento deverá funcionar como um **índice técnico pesquisável de todos os scripts relevantes do projeto**.

O objetivo é permitir que um desenvolvedor encontre rapidamente o arquivo responsável por determinada funcionalidade.

Organize os scripts por:
1. Etapa do pipeline.
2. Domínio funcional.
3. Responsabilidade técnica.

Para cada script, apresente:

- **Arquivo:** caminho relativo completo no repositório.
- **Categoria:** classificação funcional.
- **Descrição:** finalidade em uma frase.
- **Responsabilidades:** operações efetivamente realizadas.
- **Entradas:** arquivos, dados e parâmetros utilizados.
- **Saídas:** arquivos ou dados produzidos.
- **Dependências:** módulos internos e scripts relacionados.
- **Execução:** comando de utilização, quando aplicável.

Utilize tabelas para facilitar a consulta.

Exemplo ilustrativo:

| Script | Categoria | Responsabilidade | Etapa |
|---|---|---|---|
| `extract_data.py` | Extração | Obtém os dados de origem | 01 |
| `validate_data.py` | Validação | Verifica a consistência dos dados | 02 |
| `transform_data.py` | Processamento | Realiza transformações | 03 |
| `generate_output.py` | Exportação | Gera os arquivos finais | 04 |

Os nomes acima são apenas exemplos. Utilize os arquivos reais do projeto.

**Requisitos de navegabilidade:**

- Inclua links relativos para os scripts.
- Utilize os caminhos completos relativos à raiz do repositório.
- Mantenha uma nomenclatura consistente.
- Evite descrições genéricas.
- Permita localizar scripts por nome, funcionalidade ou etapa.
- Identifique scripts auxiliares, utilitários, executáveis e módulos de suporte.
- Não omita scripts relevantes apenas porque não fazem parte do fluxo principal.

Quando o projeto possuir muitos scripts, crie subdivisões por categoria ou etapa para evitar tabelas excessivamente extensas.

Não transforme esse documento em uma cópia integral do código-fonte. Seu propósito é orientar a navegação e a compreensão das responsabilidades.

### 2.13. configuration.md — Configurações

Documente:
- Arquivos de configuração.
- Variáveis de ambiente.
- Parâmetros de execução.
- Constantes relevantes.
- Diretórios de entrada e saída.
- Configurações de integração.
- Valores padrão.
- Configurações obrigatórias e opcionais.

Indique onde cada configuração é definida e quais componentes a utilizam.

Nunca exponha credenciais, tokens ou informações sensíveis.

### 2.14. data_dictionary.md — Dados e artefatos

Documente os principais dados utilizados e produzidos pelo sistema.

Inclua:
- Arquivos de entrada.
- Arquivos intermediários.
- Arquivos finais.
- Formatos utilizados.
- Estrutura e campos relevantes.
- Convenções de nomenclatura.
- Localização dos arquivos.
- Relação entre dados e etapas do pipeline.

Diferencie dados persistentes, temporários e regeneráveis.

Adapte o nível de detalhamento à natureza do projeto.

### 2.15. testing.md — Testes e validações

Documente:
- Ferramentas utilizadas.
- Organização dos testes.
- Comandos de execução.
- Testes unitários e de integração.
- Validações do pipeline.
- Verificações de consistência dos resultados.

Inclua apenas procedimentos efetivamente suportados pelo projeto.

### 2.16. troubleshooting.md — Solução de problemas

Documente problemas conhecidos e procedimentos de diagnóstico.

Organize por:
- Mensagem de erro ou sintoma.
- Possível causa.
- Como identificar o problema.
- Solução recomendada.

Não invente problemas ou soluções.

---

# 3. Boas práticas de documentação

Aplique os seguintes princípios em todos os documentos.

## Clareza e objetividade

- Utilize linguagem técnica, mas acessível.
- Prefira frases curtas e parágrafos objetivos.
- Evite redundâncias.
- Explique siglas e conceitos específicos na primeira ocorrência.
- Priorize informações práticas.
- Mantenha consistência terminológica.

## Organização e navegabilidade

- Utilize hierarquia consistente de títulos Markdown.
- Crie links relativos entre os documentos.
- Utilize tabelas para informações estruturadas.
- Utilize listas para procedimentos.
- Utilize blocos de código com identificação da linguagem.
- Crie referências cruzadas quando úteis.
- Inclua índices de navegação nos documentos extensos.

## Facilidade de busca

- Utilize nomes reais dos arquivos e caminhos completos.
- Mantenha o catálogo de scripts centralizado.
- Utilize palavras-chave nos títulos.
- Organize informações por funcionalidade e responsabilidade.
- Facilite a localização por nome de arquivo, etapa ou finalidade.
- Evite descrições abstratas como "processa os dados".

## Manutenibilidade

- Evite duplicação de informações entre documentos.
- Defina claramente a responsabilidade de cada arquivo.
- Utilize links para direcionar a informações complementares.
- Evite informações que mudam frequentemente sem necessidade.
- Mantenha comandos e exemplos sincronizados com o código.
- Documente o comportamento implementado, não funcionalidades planejadas.

## Apresentação

- Priorize legibilidade no GitHub e em editores Markdown.
- Evite excesso de emojis e elementos decorativos.
- Utilize tabelas apenas quando realmente facilitarem a leitura.
- Mantenha documentos com extensão proporcional à sua finalidade.

---

# 4. Critérios de qualidade

O resultado deverá atender aos seguintes requisitos:

1. Um novo desenvolvedor deverá compreender a finalidade do projeto em poucos minutos.
2. O README deverá ser conciso e funcionar como ponto de entrada.
3. A documentação técnica deverá estar organizada por assunto.
4. O fluxo completo do pipeline deverá estar documentado.
5. Todos os scripts relevantes deverão estar catalogados.
6. As dependências entre etapas deverão estar explícitas.
7. Os comandos de execução deverão corresponder à implementação real.
8. Os links internos deverão funcionar.
9. Os documentos não deverão apresentar informações duplicadas ou contraditórias.
10. A documentação deverá ser fácil de atualizar conforme o projeto evoluir.

# 5. Restrições e cuidados

- Não altere a implementação dos scripts.
- Não renomeie arquivos ou diretórios existentes.
- Não modifique dependências ou configurações.
- Preserve informações técnicas relevantes da documentação anterior.
- Não invente funcionalidades, comandos ou parâmetros.
- Não exponha credenciais ou dados sensíveis.
- Não crie documentos vazios ou sem conteúdo relevante.
- Não duplique desnecessariamente o conteúdo do README nos documentos complementares.
- Modifique ou crie somente arquivos de documentação, respeitando as instruções do projeto.
- Preserve documentos existentes que não precisem ser alterados.

# 6. Processo de execução

Siga rigorosamente as seguintes fases:

**Fase 1 — Diagnóstico**

Analise o repositório, sua arquitetura, pipeline, scripts e documentação existente.

**Fase 2 — Planejamento**

Defina a estrutura documental de dois níveis.

Identifique quais informações ficarão no README e quais serão distribuídas em `docs/`.

**Fase 3 — Implementação**

Reestruture o README e crie ou atualize os documentos técnicos necessários.

**Fase 4 — Revisão técnica**

Verifique:
- Cobertura dos scripts relevantes.
- Correção da sequência do pipeline.
- Existência dos caminhos documentados.
- Validade dos comandos.
- Funcionamento dos links relativos.
- Correspondência dos diagramas com o código.
- Ausência de contradições e duplicações.
- Consistência entre README e documentação complementar.
- Qualidade da renderização Markdown.

**Fase 5 — Relatório de conclusão**

Apresente:
- Melhorias realizadas.
- Nova estrutura documental.
- Documentos criados ou atualizados.
- Scripts e etapas catalogados.
- Informações que não puderam ser confirmadas.
- Lacunas de documentação identificadas.

# 7. Resultado esperado

Entregue uma documentação técnica profissional, organizada em dois níveis:

**README.md:** porta de entrada do projeto, com apresentação, instalação, execução rápida e índice da documentação.

**docs/:** conjunto de documentos técnicos detalhados, com arquitetura, pipeline, catálogo de scripts, configurações, dados, testes e solução de problemas.

O resultado deverá funcionar como um verdadeiro sistema de documentação do projeto, permitindo que desenvolvedores compreendam a arquitetura, executem o pipeline, localizem funcionalidades e realizem manutenção com rapidez e segurança.

Priorize sempre a precisão técnica, a facilidade de consulta e a manutenibilidade da documentação.