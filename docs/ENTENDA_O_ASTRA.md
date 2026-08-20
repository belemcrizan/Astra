# Entenda a v0.2 sem precisar ser tecnico

## A pergunta do teste

O programa cria uma historia financeira ficticia, esconde mudancas e acontecimentos dentro dela e pergunta: **quantos foram encontrados, quantos alarmes estavam errados e quanto tempo demorou?**

Na primeira POC, dizer apenas “encontrou tudo” escondia parte da historia. Um sistema poderia marcar muitos pontos e ainda obter recall alto. A v0.2 impede isso: cada alarme so pode corresponder a uma mudanca real, e alarmes extras reduzem precision e F1.

## Como ler as metricas

- **precision**: entre os alarmes emitidos, quantos estavam corretos;
- **recall**: entre os eventos escondidos, quantos foram encontrados;
- **F1**: equilibrio entre precision e recall;
- **falsos alarmes/1.000**: carga operacional para quem revisa;
- **atraso**: distancia entre o evento real e a deteccao;
- **IC95%**: faixa de incerteza causada pela quantidade limitada de eventos;
- **evidence score**: ranking heuristico interno; nao e probabilidade.

## O que e stacking

Tres eventos individualmente fracos podem ficar escondidos no ruido. O ASTRA alinha as janelas depois de cada evento e calcula sua resposta media, como empilhar imagens fracas do mesmo objeto.

Depois ele desloca os eventos circularmente 999 vezes, preservando a serie e sua memoria temporal. Isso cria mundos em que a associacao e falsa. O p-valor informa quantos desses mundos falsos produziram um alinhamento igual ou maior.

## Por que existem outros detectores

CUSUM, Page-Hinkley, PELT e BOCPD tentam encontrar as mesmas mudancas por metodos conhecidos. Se um deles vencer o ASTRA, o relatorio mostra isso. O objetivo nao e fabricar uma vitoria, mas descobrir onde cada metodo funciona.

## Decisao final

`human_review` significa apenas que uma pessoa deve examinar o pacote. Nao significa “verdadeiro”, “fraude” ou “compre/venda”. A POC nao executa nenhuma acao externa.

