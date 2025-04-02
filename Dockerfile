FROM python:3.9.19-slim-bullseye

COPY . /app

WORKDIR /app
RUN apt-get update && apt-get install -y redis-server &&  apt-get clean
RUN pip install -e . && mkdir -p /app/data
ENV ASYNC_ALLOW=True
CMD cd /app/data && redis-server  --daemonize yes  && python /app/examples/properties/simple_implementation/implementation.py 