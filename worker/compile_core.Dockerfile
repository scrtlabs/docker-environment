FROM enigmampc/core-compile-base:latest

ARG SGX_MODE
ARG DEBUG
ENV SGX_MODE=${SGX_MODE}
COPY --from=gitclone_core /enigma-core /root/

WORKDIR /root/enigma-core

RUN . /opt/sgxsdk/environment && env && RUSTFLAGS=-Awarnings RUST_BACKTRACE=1 make DEBUG=${DEBUG}