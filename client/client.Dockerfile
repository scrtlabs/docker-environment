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

########################
FROM base

WORKDIR /root

COPY --from=pybuild /root/wheels /root/wheels

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt

# COPY --from=gitclone /enigma-contract/enigma-js /root/enigma-contract/enigma-js
COPY enigma-js/package.json /root/enigma-contract/enigma-js/
COPY enigma-js/.babelrc /root/enigma-contract/enigma-js/
WORKDIR /root/enigma-contract/enigma-js

RUN yarn install

COPY cluster-sdk/ /root/enigma-contract/cluster-sdk/
WORKDIR /root/enigma-contract/cluster-sdk/

RUN npm install

COPY kubeconfig.eastus.json /root/enigma-contract/k8s-deployment/_output/enigma-cluster/kubeconfig/kubeconfig.eastus.json
COPY worker.yaml /root/enigma-contract/k8s-configuration/deployments/worker/worker.yaml
WORKDIR /root/enigma-contract/enigma-js

COPY enigma-js/jest.init.js /root/enigma-contract/enigma-js/
COPY enigma-js/test /root/enigma-contract/enigma-js/test
COPY enigma-js/src /root/enigma-contract/enigma-js/src
COPY enigma-js/Makefile /root/enigma-contract/enigma-js/Makefile

RUN mkdir -p /root/.enigma/

COPY config config
COPY scripts/tests_setup.py .
COPY scripts/startup.sh .

COPY --from=enigmampc/contract /root/enigma-contract/build /root/enigma-contract/build

RUN chmod +x startup.sh && chmod +x tests_setup.py

ENV ENIGMA_ENV=TESTNET
ENV SGX_MODE=SW

CMD /bin/bash -c './startup.sh';'/bin/bash'