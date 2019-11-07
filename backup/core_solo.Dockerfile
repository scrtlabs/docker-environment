#### RUN 01_core_base before this with image target name enigmampc/core-base

###### STAGE 1 -- build core
FROM baiduxlab/sgx-rust:1804-1.0.9 as core-build

LABEL maintainer=enigmampc

ARG DEBUG
ARG SGX_MODE
ENV SGX_MODE=${SGX_MODE:-SW}

ENV PATH="/root/.cargo:/root/.cargo/bin:${PATH}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends libzmq3-dev llvm clang-3.9 && \
    rm -rf /var/lib/apt/lists/*

RUN rustup target add wasm32-unknown-unknown && \
    cargo install bindgen cargo-audit && \
    cargo install sccache --features=azure && \
    rm -rf /root/.cargo/registry && \
    rm -rf /root/.cargo/git

ENV RUSTC_WRAPPER=sccache
ENV SCCACHE_AZURE_BLOB_CONTAINER="sccache"

ARG SCCACHE_AZURE_CONNECTION_STRING
ENV SCCACHE_AZURE_CONNECTION_STRING=${SCCACHE_AZURE_CONNECTION_STRING:-}

# clone the rust-sgx-sdk baidu sdk
RUN git clone --depth 1  -b v1.0.9 https://github.com/baidu/rust-sgx-sdk.git  sgx

COPY --from=gitclone_core /enigma-core /root/

WORKDIR /root/enigma-core

RUN . /opt/sgxsdk/environment && env && SGX_MODE=${SGX_MODE:-SW} RUSTFLAGS=-Awarnings RUST_BACKTRACE=1 make DEBUG=${DEBUG}

######## Stage 2 - build python wheels

FROM enigmampc/core-base:latest as pybuild

WORKDIR /root

# this is here first don't run it again unless we actually change the requirements
COPY ../core/scripts/requirements.txt ./

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-setuptools \
    gcc \
    python3.6-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install wheel

RUN pip3 wheel --wheel-dir=/root/wheels -r requirements.txt -i http://pypi.keytango.io --trusted-host pypi.keytango.io

#############################

FROM enigmampc/core-base:latest

COPY --from=pybuild /root/wheels /root/core/wheels

COPY ../core/scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/p2p/wheels \
      -r requirements.txt

COPY --from=core-build /root/enigma-core/bin/ /root/core/bin/

COPY ../core/config/core ./core/config

COPY ../core/scripts/core_startup.py ./core/

RUN chmod +x ./core/core_startup.py

COPY ../core/devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 8080

CMD . /opt/sgxsdk/environment && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf