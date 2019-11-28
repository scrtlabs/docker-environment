# build this image by cd'ing into this dir, and running
# docker build -f operator.Dockerfile -t enigma_salad_operator .
# then run `docker-compose up` in the root project directory.

FROM rust:1 as secret_contract_build

COPY --from=gitclone_core /enigma-core/rust-toolchain /root/salad/secret_contracts/salad/rust-toolchain
WORKDIR /root/salad/secret_contracts/salad

RUN rustup toolchain add $(cat rust-toolchain) --target wasm32-unknown-unknown

COPY --from=gitclone_salad /root/salad/secret_contracts/salad /root/salad/secret_contracts/salad

RUN cargo +$(cat rust-toolchain) build --release --target wasm32-unknown-unknown

##########################

FROM node:10-buster as node_modules_build

COPY --from=gitclone_salad /root/salad/package.json /root/salad/package.json
COPY --from=gitclone_salad /root/salad/yarn.lock /root/salad/yarn.lock
COPY --from=gitclone_salad /root/salad/client/package.json /root/salad/client/package.json
COPY --from=gitclone_salad /root/salad/operator/package.json /root/salad/operator/package.json
WORKDIR /root/salad

RUN : \
    && yarn install --production \
    && yarn add truffle --ignore-workspace-root-check

##########################

FROM node:10-buster

RUN : \
    && apt-get update \
    && apt-get install -y --no-install-recommends netcat

COPY --from=gitclone_salad /root/salad /root/salad
COPY --from=node_modules_build /root/salad/node_modules /root/salad/node_modules
COPY --from=node_modules_build /root/salad/client/node_modules /root/salad/client/node_modules
COPY --from=node_modules_build /root/salad/operator/node_modules /root/salad/operator/node_modules
COPY --from=secret_contract_build /root/salad/secret_contracts/salad/target/wasm32-unknown-unknown/release/contract.wasm /root/salad/salad.wasm

WORKDIR /root/salad

ARG SGX_MODE=SW
ENV SGX_MODE $SGX_MODE

RUN : \
    && yarn configure \
    && npx truffle compile

COPY scripts ./scripts/

#CMD ./scripts/run.sh
