.PHONY: demo benchmark preregistration schema test api docker clean

demo:
	python -m astra_poc demo

benchmark:
	python -m astra_poc benchmark --seeds 30

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
