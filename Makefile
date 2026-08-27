.PHONY: demo judge-demo hero-demo control-demo demo-failures real-demo benchmark ablations preregistration schema test api docker clean

demo:
	python -m astra_poc demo

judge-demo:
	python -m astra_poc judge-demo

hero-demo:
	python -m astra_poc hero-demo

control-demo:
	python -m astra_poc control-demo

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
