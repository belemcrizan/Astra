.PHONY: demo judge-demo hero-demo control-demo unknown-demo budget-demo adversarial-demo multimodal-demo pareto-frontier demo-failures real-demo benchmark ablations preregistration schema test api docker clean

demo:
	python -m astra_poc demo

judge-demo:
	python -m astra_poc judge-demo --explain-policy

hero-demo:
	python -m astra_poc hero-demo

control-demo:
	python -m astra_poc control-demo

unknown-demo:
	python -m astra_poc unknown-demo

budget-demo:
	python -m astra_poc budget-demo

adversarial-demo:
	python -m astra_poc adversarial-demo

multimodal-demo:
	python -m astra_poc multimodal-demo

pareto-frontier:
	python -m astra_poc pareto-frontier

demo-failures:
	python -m astra_poc demo-failures

real-demo:
	python -m astra_poc real-demo

benchmark:
	python -m astra_poc benchmark --seeds 30

ablations:
	python -m astra_poc ablations --seeds 15

preregistration:
	python -m astra_poc preregistration

schema:
	python -m astra_poc schema

test:
	python -m unittest discover -s tests -v

api:
	uvicorn astra_poc.api:app --reload

docker:
	docker compose up --build

clean:
	python -m astra_poc clean
