FROM brunneis/python:3.8.0-ubuntu-bionic as base
#
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends \
#    software-properties-common
#
#RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
#    python3-pip \
#    python3-setuptools \
#    python3.8-dev \
     g++ \
     gcc \
     make \
     && rm -rf /var/lib/apt/lists/*

RUN pip3 install wheel

COPY . /root/common_scripts/
WORKDIR /root/common_scripts
RUN pip3 wheel --wheel-dir=/root/wheels .
