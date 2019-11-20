FROM ubuntu:18.04 as base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    curl \
    python-dev \
    git \
    g++ \
    make \
    && curl -sL https://deb.nodesource.com/setup_10.x | bash - \
    && curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs yarn \
    && rm -rf /var/lib/apt/lists/*

######## Stage 4 - build python wheels

FROM base as pybuild

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-setuptools \
    gcc \
    python3.6-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install wheel

COPY . /root/common_scripts/
WORKDIR /root/common_scripts
RUN pip3 wheel --wheel-dir=/root/wheels .
