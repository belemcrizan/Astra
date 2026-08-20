# Pre-registro metodologico - ASTRA v0.2

Este arquivo declara as regras antes do benchmark oficial da v0.2. A fonte executavel e `src/astra_poc/preregistration.py`; toda execucao grava o SHA-256 canonico dessa configuracao no relatorio.

## Hipoteses

- H1: a serie possui ao menos uma mudanca relevante de regime de media ou volatilidade.
- H2: eventos conhecidos estao alinhados a uma resposta com a forma pre-especificada.

## Regras congeladas

- change-points usam pareamento temporal um-para-um;
- tolerancia: 3,5% do comprimento da serie, com minimo de 20 pontos;
- anomalias usam tolerancia de 2 pontos;
- intervalos binomiais: Wilson 95%;
- Signal Agent: `|z robusto| >= 7`;
- Regime Agent: janela 100, score minimo 0,75, separacao minima 240;
- H2: 999 deslocamentos temporais circulares, alternativa unilateral positiva e `alpha=0,01`;
- baselines: CUSUM, Page-Hinkley, PELT Gaussiano e BOCPD com parametros registrados no codigo;
- nenhum threshold pode ser alterado depois de observar o benchmark sem gerar nova versao metodologica.

## Metricas primarias

Precision, recall, F1, falsos alarmes por 1.000 pontos, atraso assinado, atraso absoluto e IC95% de precision/recall. Para H2: p-valor empirico, poder no sinal fixo e taxa de falso positivo quando a amplitude injetada e zero.

## Criterio de governanca

Uma hipotese so segue para `human_review` quando supera o evidence score operacional e a falsificacao pre-registrada. Exaustao, timeout ou falta de evidencia nunca produzem aprovacao automatica.

