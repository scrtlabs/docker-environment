FROM enigmampc/core-compile-base:latest as core-build

ARG DEBUG
ARG SGX_MODE
ENV SGX_MODE=${SGX_MODE}

COPY --from=gitclone_core /enigma-core /root/

WORKDIR /root/enigma-principal

RUN . /opt/sgxsdk/environment && env && make full-clean

RUN . /opt/sgxsdk/environment && env && SGX_MODE=${SGX_MODE} RUSTFLAGS=-Awarnings RUST_BACKTRACE=${DEBUG} make DEBUG=${DEBUG}

######## Stage 2 - build python wheels

FROM enigmampc/core-runtime-base:latest as pybuild

WORKDIR /root

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-setuptools \
    gcc \
    python3.6-dev \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install wheel

COPY scripts/requirements.txt ./

RUN pip3 wheel --wheel-dir=/root/wheels -r requirements.txt -i http://pypi.keytango.io --trusted-host pypi.keytango.io

####### Stage 3

FROM enigmampc/core-runtime-base:latest

RUN mkdir -p /tmp/contracts

WORKDIR /root

COPY --from=pybuild /root/wheels /root/core/wheels

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/root/core/wheels \
      -r requirements.txt

COPY --from=core-build /root/enigma-principal/bin ./bin

COPY scripts ./scripts
RUN chmod +x ./scripts/km_startup.py

COPY config ./config

COPY devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 3040

CMD . /opt/sgxsdk/environment && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf