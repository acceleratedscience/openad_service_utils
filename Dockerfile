FROM python:3.9.19-slim-bullseye

COPY . /app

WORKDIR /app
RUN apt-get update && apt-get install -y redis-server &&  apt-get clean
RUN pip install -e .
ENV ASYNC_ALLOW=True
CMD  redis-server --daemonize yes && python examples/properties/simple_implementation/implementation.py 