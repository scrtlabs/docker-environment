#### RUN 01_core_base before this with image target name enigmampc/core-base

###### STAGE 1 -- build core
FROM baiduxlab/sgx-rust:1804-1.0.9

LABEL maintainer=enigmampc

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