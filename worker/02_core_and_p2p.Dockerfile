#### RUN 01_core_base before this with image target name enigmampc/core-base

###### STAGE 1 -- build core
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
    # cargo install sccache --features=azure && \
    rm -rf /root/.cargo/registry && \
    rm -rf /root/.cargo/git

# ENV RUSTC_WRAPPER=sccache
# ENV SCCACHE_AZURE_BLOB_CONTAINER="sccache"

# ARG SCCACHE_AZURE_CONNECTION_STRING
# ENV SCCACHE_AZURE_CONNECTION_STRING=${SCCACHE_AZURE_CONNECTION_STRING:-}

# clone the rust-sgx-sdk baidu sdk
RUN git clone --depth 1  -b v1.0.9 https://github.com/baidu/rust-sgx-sdk.git  sgx

COPY --from=gitclone_core /enigma-core /root/

WORKDIR /root/enigma-core

RUN . /opt/sgxsdk/environment && env && RUSTFLAGS=-Awarnings RUST_BACKTRACE=1 make DEBUG=${DEBUG}

###### Stage 2 - install node 10 so we can also run and compile p2p

FROM enigmampc/core-base:latest as p2p_base

LABEL maintainer=enigmampc

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && curl -sL https://deb.nodesource.com/setup_10.x | bash - \
 && curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -

RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update \
 && apt-get install -y --no-install-recommends yarn nodejs \
 && rm -rf /var/lib/apt/lists/*
######## Stage 3 - compile p2p

FROM p2p_base as p2p_build

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    gnupg \
    gcc \
    g++ \
    git \
 && rm -rf /var/lib/apt/lists/*

COPY --from=gitclone_p2p /enigma-p2p/package.json ./

# RUN npm -g config set user root

RUN npm install

# clean up npm packages (should be pretty safe)
RUN npm install -g modclean
RUN modclean -n default:safe -r

COPY --from=gitclone_p2p /enigma-p2p/src ./src/
COPY --from=gitclone_p2p /enigma-p2p/configs ./configs
COPY --from=gitclone_p2p /enigma-p2p/test/testUtils ./test/testUtils

######## Stage 4 - build python wheels

FROM enigmampc/core-base:latest as pybuild

WORKDIR /root

# this is here first don't run it again unless we actually change the requirements
COPY scripts/requirements.txt ./

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-setuptools \
    gcc \
    python3.6-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install wheel

RUN pip3 wheel --wheel-dir=/root/wheels -r requirements.txt -i http://pypi.keytango.io --trusted-host pypi.keytango.io

####### Stage 6 - add p2p folder and compiled core together

FROM p2p_base

WORKDIR /root

COPY --from=pybuild /root/wheels /root/core/wheels

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/root/core/wheels \
      -r requirements.txt

COPY --from=core-build /root/enigma-core/bin/ /root/core/bin/
COPY --from=p2p_build /app ./p2p/

EXPOSE 8080

COPY config/core ./core/config
COPY config/p2p ./p2p/config

COPY scripts/core_startup.py ./core/
COPY scripts ./p2p/scripts

RUN chmod +x ./p2p/scripts/p2p_startup.py && chmod +x ./core/core_startup.py

COPY devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD . /opt/sgxsdk/environment && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf