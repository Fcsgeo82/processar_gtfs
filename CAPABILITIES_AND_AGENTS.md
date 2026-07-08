# Capabilities And Agents

Este documento resume as capacidades principais e os agentes especializados disponíveis no ambiente **Antigravity** integrado ao ecossistema **Everything Claude Code (ECC)**.

## 🛠️ Capacidades do Sistema (Core Capabilities)
As capacidades base (tools) permitem que o assistente interaja diretamente com o sistema operacional, arquivos e rede.

| Capacidade | Descrição |
| :--- | :--- |
| **run_command** | Execução de comandos nativos no terminal (PowerShell/Bash). |
| **write_to_file** | Criação e gerenciamento de novos arquivos no workspace. |
| **replace_file_content** | Edição precisa de blocos de código em arquivos existentes. |
| **view_file** | Leitura de conteúdos de arquivos (texto e mídia). |
| **list_dir** | Exploração da estrutura de diretórios e arquivos. |
| **grep_search** | Busca avançada de padrões (regex) em todo o repositório. |
| **search_web** | Pesquisa na internet por documentação e soluções atualizadas. |
| **read_browser_page** | Interação visual e extração de dados de páginas web complexas. |
| **generate_image** | Criação de assets visuais e mockups de interface (UI/UX). |

## 🤖 Agentes Especializados (ECC Subagents)
O ecossistema ECC fornece **48 agentes especializados** que podem ser delegados para tarefas específicas, garantindo foco e profundidade técnica.

| Agente | Propósito Principal | Quando Invocar |
| :--- | :--- | :--- |
| **planner** | Planejamento estratégico | Antes de iniciar implementações complexas. |
| **architect** | Design de sistemas | Definição de arquitetura e escalabilidade. |
| **tdd-guide** | Desenvolvimento TDD | Garantia de qualidade com testes antes do código. |
| **code-reviewer** | Auditoria de qualidade | Revisão de padrões, legibilidade e performance. |
| **security-reviewer** | Segurança Ofensiva | Detecção de vulnerabilidades e falhas de lógica. |
| **build-error-resolver** | Resolução de bugs | Quando o ambiente ou o build apresenta falhas. |
| **database-reviewer** | Especialista SQL/NoSQL | Otimização de queries e design de esquemas. |
| **python-reviewer** | Especialista Python | Revisão profunda de lógica e padrões Pythonic. |
| **doc-updater** | Gestão de Conhecimento | Manter READMEs e documentações técnicas em dia. |
| **loop-operator** | Automação de Loops | Execução de tarefas repetitivas com monitoramento. |

## 🎓 Skills e Workflows (Capacidades de Domínio)
As **Skills** (182 disponíveis) são "playbooks" de conhecimento que guiam o comportamento do assistente em fluxos específicos.

*   **TDD Workflow**: Garantia de 80%+ de cobertura de testes.
*   **Security Shield**: Auditoria contínua baseada em AgentShield.
*   **Verification Loops**: Ciclos automatizados de validação de código.
*   **Architecture Patterns**: Aplicação de Hexagonal, MVC e Repository.
*   **Continuous Learning**: Extração de "instincts" (padrões aprendidos) do repo.
*   **Performance Tuning**: Otimização de tokens e latência de processamento.

## ⌨️ Comandos Rápidos (Slash Commands)
Atalhos para as funções mais utilizadas no dia a dia do desenvolvedor:

*   `/plan`: Decompõe um problema em fases de implementação.
*   `/code-review`: Realiza uma auditoria imediata nos arquivos alterados.
*   `/tdd`: Inicia o ciclo Vermelho-Verde-Refatorar.
*   `/security-scan`: Executa varredura de segurança contra vulnerabilidades.
*   `/update-docs`: Sincroniza a documentação técnica com o estado do código.
*   `/sessions`: Gerencia o histórico e o contexto das sessões de trabalho.

---
*Gerado automaticamente pelo Antigravity em 08/05/2026.*
