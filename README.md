# ASTRA POC v0.2

POC local e passiva para testar deteccao de sinais fracos, anomalias e mudancas de regime em dados **exclusivamente sinteticos**. A v0.2 corrige a avaliacao circular da primeira versao: reporta precision, recall, F1, falsos alarmes, atraso, IC95%, baselines fortes e stacking com nulo temporal.

> Isto e um teste de sanidade sintetico, nao validacao de mercado, decisao de AML nem recomendacao de investimento.

## Instalacao no Windows PowerShell

Depois de descompactar, entre na pasta que contem `pyproject.toml`:

```powershell
cd .\astra-poc-v0.2
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Se `Test-Path .\pyproject.toml` nao retornar `True`, voce ainda esta na pasta errada.

## macOS ou Linux

```bash
cd astra-poc-v0.2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Requisito: Python 3.12 ou superior.

## Primeiro teste

```powershell
python -m astra_poc demo
```

O terminal exibira precision, recall, F1, atraso, p-valor de H2 e latencia. O pacote completo para revisao humana sera salvo em `artifacts\reports\`.

## Benchmark com 30 sementes

```powershell
python -m astra_poc benchmark --seeds 30
```

O benchmark compara ASTRA, CUSUM, Page-Hinkley, PELT e BOCPD. Tambem mede H2 com sinal injetado e com amplitude zero para estimar falso positivo do stacking.

## Outros comandos

```powershell
python -m astra_poc preregistration
python -m astra_poc schema
python -m unittest discover -s tests -v
python -m astra_poc clean
```

- `preregistration`: mostra thresholds e SHA-256 metodologico;
- `schema`: exporta o JSON Schema do relatorio;
- `clean`: remove somente resultados gerados.

## O que mudou da v0.1

- pareamento temporal um-para-um;
- precision, recall, F1 e falsos alarmes por 1.000 pontos;
- atraso de deteccao assinado e absoluto;
- IC95% de Wilson;
- CUSUM, Page-Hinkley, PELT e BOCPD;
- H2 por stacking com 999 deslocamentos circulares;
- teste de H2 sob sinal zero;
- thresholds pre-registrados e hash em todo relatorio;
- `confidence` removida; agora o campo e `evidence_score` e declara ser nao calibrado;
- watermark e hash no dataset sintetico;
- pacote detalhado para revisao humana;
- dataset card, ameacas a validade e tabela unica de agentes.

## Arquitetura

```text
Dados sinteticos + hash
        |
Orchestrator Agent
        |
Analises em paralelo + baselines
        |
Hypothesis -> Falsification -> Governance
        |
Relatorio humano + JSON + telemetria
```

O LLM nao faz parte da v0.2. O plano de raciocinio futuro devera emitir apenas uma DSL restrita de testes, nunca Python arbitrario.

## Documentacao

- [Explicacao para nao tecnicos](docs/ENTENDA_O_ASTRA.md)
- [Pre-registro](PREREGISTRATION.md)
- [Agentes e metodos](docs/AGENTES_E_METODOS.md)
- [Dataset card](docs/DATASET_CARD.md)
- [Protocolo de validacao](docs/VALIDACAO.md)
- [Ameacas a validade](docs/THREATS_TO_VALIDITY.md)
- [Modelo de ameacas STRIDE](docs/THREAT_MODEL_STRIDE.md)
- [Arquitetura e fases futuras](docs/ARQUITETURA_E_MIGRACAO.md)
- [Resultado de sanidade v0.2](docs/RESULTADO_SANIDADE_V02.md)

## Proximas fases, fora deste pacote

1. familias GARCH, Markov-switching, Hawkes, jump-diffusion e caudas pesadas;
2. curvas precision/recall por SNR e limiar de deteccao em 50%;
3. calibracao temporal do evidence score;
4. Adversary Agent, drift e threat model STRIDE;
5. plano LLM por DSL restrita;
6. benchmark multicloud por paridade semantica.
