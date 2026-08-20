# Dataset card - mercado sintetico v2

## Finalidade

Testar mecanica, reprodutibilidade e metricas do ASTRA sem usar dados pessoais ou financeiros reais. O dataset nao representa fielmente nenhum mercado.

## Conteudo

- 2.400 observacoes por padrao;
- tres regimes Gaussianos com medias e volatilidades diferentes;
- duas anomalias pontuais;
- tres eventos com uma resposta fraca de nove passos;
- preco derivado dos retornos e volume log-normal condicionado ao regime.

## Verdade sintetica

As mudancas, anomalias e eventos sao retidos apenas pelo avaliador. Cada dataset carrega:

- watermark `SYNTHETIC_ONLY_NOT_REAL_DATA`;
- versao, semente e amplitude;
- hash SHA-256 dos arrays observados.

## Usos adequados

- testes unitarios e de integracao;
- comparacao controlada de detectores;
- verificacao de reprodutibilidade;
- estudo de comportamento sob sinal zero ou sinal injetado.

## Usos inadequados

- estimar performance em mercado real;
- tomar decisoes de investimento ou AML;
- afirmar causalidade;
- treinar politicas de intervencao sobre pessoas.

## Limitacoes

O gerador e os detectores ainda compartilham premissas, a escala temporal nao representa segundos/dias reais, ha poucos eventos por execucao e nao ha custos de transacao, microestrutura completa ou comportamento adaptativo.

