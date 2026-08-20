# Protocolo de validacao da v0.2

## Controles implementados

- ground truth oculto dos agentes e visivel ao avaliador;
- pareamento one-to-one com tolerancia pre-registrada;
- precision, recall, F1, falsos alarmes e atraso;
- Wilson 95% para proporcoes;
- quatro baselines com parametros publicados;
- stacking de H2 com 999 nulos circulares;
- teste adicional de H2 com amplitude zero;
- dataset, metodologia, semente e hashes no relatorio;
- mesma semente reproduz arrays, p-valor e saidas numericas dentro de tolerancia;
- teste automatizado do JSON Schema e ausencia do antigo campo `confidence`.

## Interpretacao dos intervalos

Dois acertos em dois eventos produzem recall pontual de 100%, mas o limite inferior de Wilson fica perto de 34%. Em 30 runs, 60/60 acertos elevam o limite inferior para aproximadamente 94%. Isso reduz incerteza amostral dentro do gerador, mas nao resolve validade externa.

## Justica entre metodos

Todos recebem a mesma serie e sao avaliados pelo mesmo pareamento. Seus parametros estao congelados no pre-registro. Ainda assim, nao afirmamos que o tuning foi igualmente otimo; isso permanece uma ameaca a validade.

## Criterio de sucesso honesto

A v0.2 passa como POC de engenharia se for reproduzivel, observavel e degradar com seguranca. Como resultado cientifico, ela apenas produz uma linha de base. Um baseline forte pode empatar ou vencer sem invalidar a arquitetura.

