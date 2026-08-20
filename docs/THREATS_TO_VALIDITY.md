# Ameacas a validade

## Validade interna

- Detector e gerador podem compartilhar premissas de forma/volatilidade.
- Escolhas de threshold podem favorecer o dataset, apesar do pre-registro.
- Baselines possuem sensibilidades diferentes aos hiperparametros.
- H1 usa confirmacao algorítmica no mesmo dataset; isso nao cria uma fonte de evidencia independente.

Mitigacao: thresholds versionados, parametros publicados, pareamento um-para-um, sinal zero para H2 e resultados completos inclusive quando um baseline vence.

## Validade externa

Trinta sementes do mesmo gerador nao representam mercados, AML ou mensagens reais. Nenhuma metrica deve ser extrapolada para producao.

Mitigacao futura: familias Markov-switching, GARCH, jump-diffusion, Hawkes, caudas pesadas, drift gradual, missing data e dados autorizados em shadow mode.

## Validade de construto

- `evidence_score` e heuristico, nao probabilidade calibrada.
- Tolerancia em pontos nao possui unidade economica.
- Stacking mede associacao alinhada, nao efeito causal.
- Susceptibilidade e entropia sao observaveis exploratorios.

## Validade de conclusao

ICs de Wilson refletem contagens finitas, nao incerteza sobre novos mundos. Multiplicidade esta controlada apenas para a unica H2 atual. Comparacoes futuras exigem correcao Benjamini-Hochberg ou procedimento equivalente.

