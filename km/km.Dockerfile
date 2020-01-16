FROM enigmampc/core-compile-base:latest as core-build

ARG DEBUG
ARG SGX_MODE
ENV SGX_MODE=${SGX_MODE}

COPY --from=gitclone_core /enigma-core /root/

WORKDIR /root/enigma-principal

RUN . /opt/sgxsdk/environment && env && make full-clean

RUN . /opt/sgxsdk/environment && env && SGX_MODE=${SGX_MODE} RUSTFLAGS=-Awarnings RUST_BACKTRACE=${DEBUG} make DEBUG=${DEBUG}


####### Stage 3

FROM enigmampc/core-runtime-base:develop

RUN mkdir -p /tmp/contracts

WORKDIR /root

COPY --from=enigma_common /root/wheels /root/wheels

RUN pip3 install supervisor

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/root/wheels \
      -r requirements.txt

COPY --from=core-build /root/enigma-principal/bin ./bin

COPY scripts ./scripts
RUN chmod +x ./scripts/km_startup.py

COPY config ./config

COPY devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 3040

ENTRYPOINT . /opt/sgxsdk/environment && supervisord -c /etc/supervisor/conf.d/supervisord.conf