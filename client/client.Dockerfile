ARG DOCKER_TAG
FROM brunneis/python:3.8.0-ubuntu-bionic as base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    g++ \
    make \
    && curl -sL https://deb.nodesource.com/setup_10.x | bash - \
    && curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
    && echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs yarn \
    && rm -rf /var/lib/apt/lists/*

########################
FROM enigmampc/contract:${DOCKER_TAG} AS contract
FROM base

WORKDIR /root

COPY --from=enigma_common /root/wheels /root/wheels

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt

COPY --from=gitclone_integration /integration-tests /root/integration-tests
COPY --from=gitclone_contract /enigma-contract/enigma-js/lib/enigma-js.node.js /root/integration-tests/enigma-js/lib/enigma-js.node.js


COPY --from=contract /root/enigma-contract/build /root/build

WORKDIR /root/integration-tests
RUN yarn install

RUN mkdir -p /root/.enigma/

COPY config config
COPY scripts/tests_setup.py .
COPY scripts/startup.sh .
COPY scripts/Makefile .

RUN chmod +x startup.sh && chmod +x tests_setup.py

ENV ENIGMA_ENV=TESTNET
ENV SGX_MODE=SW

ENTRYPOINT /bin/bash -c './startup.sh';'/bin/bash'
