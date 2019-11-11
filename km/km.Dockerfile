FROM baiduxlab/sgx-rust:1804-1.0.9 as core-build

LABEL maintainer=enigmampc

ARG DEBUG

ARG SGX_MODE

ENV SGX_MODE=${SGX_MODE}

ENV PATH="/root/.cargo:/root/.cargo/bin:${PATH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends libzmq3-dev llvm clang-3.9 && \
    rm -rf /var/lib/apt/lists/*

RUN rustup target add wasm32-unknown-unknown && \
    cargo install bindgen && \
    rm -rf /root/.cargo/registry && \
    rm -rf /root/.cargo/git

# clone the rust-sgx-sdk baidu sdk
RUN git clone --depth 1  -b v1.0.9 https://github.com/baidu/rust-sgx-sdk.git  sgx

COPY --from=gitclone_core /enigma-core /root/

WORKDIR /root/enigma-principal

RUN . /opt/sgxsdk/environment && env && make full-clean

RUN . /opt/sgxsdk/environment && env && SGX_MODE=${SGX_MODE} RUSTFLAGS=-Awarnings RUST_BACKTRACE=${DEBUG} make DEBUG=${DEBUG}

######## Stage 2 - build python wheels

FROM enigmampc/core-base:latest as pybuild

WORKDIR /root

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-setuptools \
    gcc \
    python3.6-dev \
 && rm -rf /var/lib/apt/lists/*

COPY scripts/requirements.txt ./

RUN pip3 install wheel

RUN pip3 wheel --wheel-dir=/root/wheels -r requirements.txt -i http://pypi.keytango.io --trusted-host pypi.keytango.io

####### Stage 3

FROM enigmampc/core-base:latest

RUN mkdir -p /tmp/contracts

WORKDIR /root

COPY --from=pybuild /root/wheels /root/core/wheels

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/root/core/wheels \
      -r requirements.txt

COPY --from=core-build /root/enigma-principal/bin ./bin

COPY scripts ./scripts
RUN chmod +x ./scripts/km_startup.py

COPY config ./config

COPY devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 3040

CMD . /opt/sgxsdk/environment && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf