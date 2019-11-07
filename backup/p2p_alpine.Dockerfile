FROM node:10-alpine as build

COPY --from=gitclone /enigma-p2p/package.json ./build/

WORKDIR build/

RUN apk add --no-cache --virtual .gyp \
        python \
        make \
        g++ \
        git \
        bash \
    && npm install \
    && apk del .gyp

RUN npm install -g modclean
RUN modclean -n default:safe -r

COPY --from=gitclone /enigma-p2p/src ./build/src/
COPY --from=gitclone /enigma-p2p/configs ./build/configs
COPY --from=gitclone /enigma-p2p/test/testUtils ./build/test/testUtils

########################################

FROM node:10-alpine as pybuild

RUN apk add --no-cache \
    python3-dev=3.6.9-r2 \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && apk add --no-cache --update python3 \
    && pip3 install --upgrade pip setuptools wheel

COPY scripts/requirements.txt .
#RUN pip3 install -r requirements.txt -i http://pypi.keytango.io --trusted-host pypi.keytango.io

RUN pip3 wheel --wheel-dir=/root/wheels -r requirements.txt -i http://pypi.keytango.io --trusted-host pypi.keytango.io

###################################

FROM node:10-alpine

RUN apk add --no-cache \
    supervisor \
    bash \
    python3

COPY --from=build ./build ./p2p
COPY --from=pybuild /root/wheels /p2p/wheels

COPY scripts/requirements.txt .

RUN pip3 install \
      --no-index \
      --find-links=/p2p/wheels \
      -r requirements.txt

EXPOSE 8080

COPY config/p2p ./p2p/config

COPY scripts/p2p_startup.py ./p2p/

RUN chmod +x ./p2p/p2p_startup.py

COPY devops/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]