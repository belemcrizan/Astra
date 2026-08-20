# Resultado de sanidade em dados sinteticos - v0.2

Este documento deve ser atualizado somente a partir de `astra benchmark --seeds 30`. Os resultados incluidos no pacote foram produzidos em 20 de agosto de 2026 no ambiente local de desenvolvimento.

## Leitura correta

O benchmark mede se a implementacao recupera estruturas do gerador e como se compara a baselines pre-registrados. Nao mede eficacia em mercado real, AML ou causalidade.

Consulte `artifacts/reports/benchmark-v0.2-latest.md` para a tabela produzida automaticamente. Nesta versao, PELT pode superar o ASTRA no mesmo gerador; isso e reportado como resultado valido, nao ocultado.

## Resultado empacotado - 30 sementes, 2.400 pontos

| Metodo de regime | Precision | Recall | F1 | Falsos alarmes/1.000 | Atraso abs. medio |
|---|---:|---:|---:|---:|---:|
| ASTRA | 75,0% | 100,0% | 85,7% | 0,278 | 8,05 |
| PELT-Gaussian | 100,0% | 100,0% | 100,0% | 0,000 | 2,62 |
| BOCPD-NIG | 41,7% | 71,7% | 52,8% | 0,833 | 11,88 |
| Page-Hinkley | 16,3% | 100,0% | 28,0% | 4,278 | 22,23 |
| CUSUM | 13,7% | 100,0% | 24,1% | 5,236 | 24,37 |

- ASTRA: IC95% de recall 93,98%-100%; IC95% de precision 64,52%-83,19%.
- H2 significativa no sinal fixo: 73,3% das sementes (IC95% 55,55%-85,82%).
- H2 falso positivo com amplitude zero: 3,3% (1/30; IC95% 0,59%-16,67%).
- Latencia ponta a ponta p95 no ambiente de desenvolvimento: 432,51 ms.
- Nenhuma falha de agente.

PELT venceu o detector ASTRA neste gerador em precision, F1 e atraso. Isso mostra que o valor atual da POC esta principalmente na avaliacao governada e falsificavel, nao em superioridade do detector.
