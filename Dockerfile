FROM python:3.9.19-slim-bullseye

COPY . /app

WORKDIR /app

RUN pip install -e .

CMD [ "python", "examples/properties/run_server.py" ]