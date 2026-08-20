# Modelo de ameacas STRIDE - escopo local v0.2

| Categoria | Ameaca | Controle atual | Lacuna antes de dados reais |
|---|---|---|---|
| Spoofing | dataset real apresentado como sintetico | watermark, versao e hash no relatorio | assinatura de origem e IAM |
| Tampering | alteracao de dataset, thresholds ou relatorio | SHA-256 de dataset e pre-registro | assinatura de artefatos e storage imutavel |
| Repudiation | negar qual configuracao produziu uma decisao | run_id, correlation_id, timestamp e logs JSON | identidade autenticada do operador |
| Information disclosure | logs guardarem conteudo sensivel | POC usa somente sintese e evita prompts | classificacao, redacao, criptografia e DLP |
| Denial of service | agente lento ou travado | timeout, retry limitado e circuit breaker | quotas, fila, backpressure e autoscaling |
| Elevation of privilege | componente executar acao externa | modo passivo e nenhuma credencial externa | sandbox, egress deny e autorizacao fina |

## Invariantes

- nenhum agente executa trades, bloqueios, acusacoes ou mensagens;
- nenhum LLM ou executor de codigo livre existe na v0.2;
- dataset sem watermark sintetico deve ser rejeitado em futuros adaptadores;
- erro, timeout ou exaustao degradam para revisao/insuficiencia, nunca aprovacao.

## Retencao

Os artefatos locais sao demonstrativos. A politica recomendada e sete dias, com remocao manual por `python -m astra_poc clean`. A POC nao apaga arquivos automaticamente para evitar perda inesperada. Antes de shadow mode, a retencao deve ser automatizada, auditada e definida por classe de dado.

