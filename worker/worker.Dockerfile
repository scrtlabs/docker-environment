###### STAGE 1 -- build core
ARG DOCKER_TAG=latest
ARG CORE_IMAGE=enigmampc/core-artifact-sw:develop
FROM $CORE_IMAGE as core-build

###### Stage 2 - install node 10 so we can also run and compile p2p

FROM enigmampc/core-runtime-base:develop as p2p_base

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
    python \
 && rm -rf /var/lib/apt/lists/*

COPY --from=gitclone_p2p /enigma-p2p/package.json ./
COPY --from=gitclone_p2p /git_commit ./git_commit
# RUN npm -g config set user root

RUN npm install

# clean up npm packages (should be pretty safe)
RUN npm install -g modclean
RUN modclean -n default:safe -r

COPY --from=gitclone_p2p /enigma-p2p/src ./src/
COPY --from=gitclone_p2p /enigma-p2p/configs ./configs
COPY --from=gitclone_p2p /enigma-p2p/test/testUtils ./test/testUtils

###### Build Worker & CLI dependencies

FROM enigma_common as pybuild

RUN pip3 wheel --wheel-dir=/root/wheels supervisor

WORKDIR /root/common_scripts
RUN pip3 wheel --wheel-dir=/root/wheels .

# install init dependencies
COPY scripts/requirements.txt .
RUN pip3 wheel \
    --find-links=/root/wheels \
    --wheel-dir=/root/wheels \
    -r requirements.txt

COPY scripts/cli/requirements.txt requirements_cli.txt
RUN pip3 wheel \
    --find-links=/root/wheels \
    --wheel-dir=/root/wheels \
    -r requirements_cli.txt

####### Stage 4 - add p2p folder and compiled core together

FROM p2p_base

WORKDIR /root

COPY --from=pybuild /root/wheels /root/wheels

RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      supervisor

# install init dependencies
COPY scripts/requirements.txt .
RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt

# install CLI dependencies
COPY scripts/cli/requirements.txt cli_requirements.txt
RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      -r cli_requirements.txt

COPY --from=core-build /root/enigma-core/bin/ /root/core/bin/
COPY --from=core-build /root/enigma-core/git_commit /root/core/git_commit

COPY --from=p2p_build /app ./p2p/
COPY --from=p2p_build /app/git_commit ./p2p/git_commit

EXPOSE 8080

COPY config/core ./core/config
COPY config/p2p ./p2p/config

COPY scripts/core_startup.py ./core/
COPY scripts ./p2p/scripts

RUN chmod +x ./p2p/scripts/p2p/start.py && chmod +x ./core/core_startup.py
RUN chmod +x ./p2p/scripts/cli/cli.py
COPY devops/supervisord.conf /etc/supervisor/supervisord.conf

##### FOR NOW TILL I FIND A WAY TO SET THESE INSIDE PYTHON :'(
ENV LD_LIBRARY_PATH=/opt/intel/libsgx-enclave-common/aesm:/opt/sgxsdk/sdk_libs:/opt/sgxsdk/sdk_libs
ENV PKG_CONFIG_PATH=:/opt/sgxsdk/pkgconfig:/opt/sgxsdk/pkgconfig
ENV SGX_SDK=/opt/sgxsdk
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/sgxsdk/bin:/opt/sgxsdk/bin/x64:/opt/sgxsdk/bin:/opt/sgxsdk/bin/x64

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN ln -s /root/p2p/scripts/cli/cli.py /usr/bin/cli

ENTRYPOINT . /opt/sgxsdk/environment && supervisord -c /etc/supervisor/supervisord.conf
# CMD ["/usr/bin/python", "/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]