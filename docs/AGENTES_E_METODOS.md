# Agentes e metodos da v0.2

| Papel | Entrada | Metodo principal | Saida | Execucao |
|---|---|---|---|---|
| Orchestrator | dataset e configuracao | grafo, timeout, retry e circuit breaker | investigacao versionada | controle |
| Signal | retornos e template | z robusto, correlacao e matched filter | anomalias e candidatos | paralelo |
| Regime | retornos | contraste local de media e volatilidade | change-points | paralelo |
| Physics | retornos | entropia, variancia extensiva, autocorrelacao e relaxacao | observaveis | paralelo |
| Graph | eventos e movimentos | proximidade temporal | grafo de evidencias | paralelo |
| Causal/Response | eventos, retornos e template | stacking + nulo circular | p-valor empirico | paralelo |
| Hypothesis | resultados tipados | composicao deterministica v0.2 | H1/H2 testaveis | sequencial |
| Falsification | hipoteses, PELT e stacking | confirmacao por metodo alternativo e nulo temporal | passed/challenged | sequencial |
| Governance | hipoteses e falhas | politicas deterministicas | human review/insufficient | gate final |

## Por que agentes e nao apenas um pipeline

Na v0.2 os componentes continuam deterministas, mas possuem contrato, timeout, falha, telemetria e substituicao independentes. Isso permite isolamento operacional e futura heterogeneidade sem acoplar o nucleo numerico a um LLM. O termo agente descreve a unidade operacional; nao implica autonomia cognitiva nesta versao.

## Physics Agent

Para uma janela com retornos `x`, a susceptibilidade exploratoria e proporcional a `N Var(x)`. A entropia e calculada sobre histograma normalizado, a memoria curta por autocorrelacao de lag 1 e o tempo de relaxacao aproximado por `-1/log(|rho_1|)`. Esses observaveis nao substituem modelos financeiros e ainda nao constituem um resultado de econofisica.

