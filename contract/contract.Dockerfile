########### STAGE 1
FROM ubuntu:18.04 as contract_base

LABEL maintainer='info@enigma.co'

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    curl \
    python3-pip \
    # for startup script wait till ganache is up
    iproute2 \
    supervisor \
    make \
    # for npm install to run migrate
 && pip3 install --upgrade pip \
 && curl -sL https://deb.nodesource.com/setup_10.x | bash - \
 && curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -

RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update \
 && apt-get install -y --no-install-recommends yarn nodejs \
 && rm -rf /var/lib/apt/lists/*

RUN npm -g config set user root

RUN npm install -g truffle@5.1.2 ganache-cli


############ STAGE 2 -- compile smart contracts
FROM contract_base as contract_compile

COPY --from=gitclone_contract /enigma-contract /root/enigma-contract

WORKDIR /root/enigma-contract/

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    git \
    g++

RUN yarn
RUN truffle compile
#
#RUN npm install -g modclean
#RUN modclean -n default:safe -r

############ STAGE 3 - install truffle/ganache/etc. node requirements
FROM node:10 as ethereum_node_builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    # for npm install
    git \
    g++ \
    make \
 && rm -rf /var/lib/apt/lists/*

COPY --from=gitclone_contract /enigma-contract/package.json /root/enigma-contract/package.json

WORKDIR /root/enigma-contract/

RUN npm install

RUN npm install -g modclean
RUN modclean -n default:safe -r

############ STAGE 4 -- Final image with only required runtime components - built contracts, node_modules, and
FROM contract_base

WORKDIR /root/enigma-contract

RUN mkdir -p /root/.enigma
RUN mkdir -p ./build/contracts/

COPY --from=enigma_common /root/wheels /root/wheels
COPY scripts/requirements.txt .
RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt

COPY --from=contract_compile /root/enigma-contract/build/contracts /root/enigma-contract/build/contracts
COPY --from=ethereum_node_builder /root/enigma-contract/node_modules /root/enigma-contract/node_modules
COPY --from=ethereum_node_builder /root/enigma-contract/package.json /root/enigma-contract/
COPY --from=gitclone_contract /enigma-contract/migrations /root/enigma-contract/migrations
COPY --from=gitclone_contract /enigma-contract/truffle.js /root/enigma-contract/

COPY scripts ./scripts/
COPY config ./config/

RUN chmod +x ./scripts/contract_server.py && chmod +x ./scripts/migrate.sh && chmod +x ./scripts/faucet_service.py

COPY devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 9545
EXPOSE 8081
EXPOSE 8001

CMD /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
