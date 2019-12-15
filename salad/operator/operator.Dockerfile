# Build this image by cd'ing into this dir, and running
# docker build -f operator.Dockerfile -t enigmampc/salad_operator .
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

# Install required dependencies + yarn and then clean the node_modules directory
RUN : \
    && rm -rf operator/node_modules client/node_modules \
    && yarn install --production \
    && yarn add truffle@5.1.2 --ignore-workspace-root-check \
    && npm install -g modclean \
    && modclean -n default:safe -r

##########################

FROM enigmampc/core-runtime-base:latest

ARG SGX_MODE=SW
ENV SGX_MODE $SGX_MODE
WORKDIR /root/salad

# Install curl, yarn, and node through APT
RUN : \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -sL https://deb.nodesource.com/setup_10.x | bash - \
    && curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends yarn nodejs

# Install the python framework
COPY --from=enigma_common /root/wheels /root/wheels
COPY scripts/requirements.txt .

RUN pip3 install \
    --no-index \
    --find-links=/root/wheels \
    -r requirements.txt

COPY --from=gitclone_salad /root/salad/operator /root/salad/operator
COPY --from=gitclone_salad /root/salad/client /root/salad/client
COPY --from=gitclone_salad /root/salad/smart_contracts /root/salad/smart_contracts
COPY --from=gitclone_salad /root/salad/migrations /root/salad/migrations
COPY --from=gitclone_salad /root/salad/package.json /root/salad/
COPY --from=gitclone_salad /root/salad/truffle.js /root/salad/
COPY --from=gitclone_salad /root/salad/.env.template /root/salad/

COPY --from=node_modules_build /root/salad/node_modules /root/salad/node_modules
COPY --from=node_modules_build /root/salad/client/node_modules /root/salad/client/node_modules
COPY --from=node_modules_build /root/salad/operator/node_modules /root/salad/operator/node_modules
COPY --from=secret_contract_build /root/salad/secret_contracts/salad/target/wasm32-unknown-unknown/release/contract.wasm /root/salad/salad.wasm

# Set up the environment variable defaults and compile the smart contracts
RUN : \
    && cp '.env.template' '.env'\
    && cp 'operator/.env.template' 'operator/.env' \
    && npx truffle compile

COPY config/ config/
COPY scripts/ scripts/

CMD ./scripts/run.sh
