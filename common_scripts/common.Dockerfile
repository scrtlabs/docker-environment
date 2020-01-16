FROM brunneis/python:3.8.0-ubuntu-bionic as base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
     g++ \
     gcc \
     make \
     && rm -rf /var/lib/apt/lists/*

RUN pip3 install wheel

COPY . /root/common_scripts/
WORKDIR /root/common_scripts
RUN pip3 wheel --wheel-dir=/root/wheels .
