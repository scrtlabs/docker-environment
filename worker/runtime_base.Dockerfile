FROM brunneis/python:3.8.0-ubuntu-bionic

LABEL maintainer=enigmampc

# SGX version parameters
ARG SGX_VERSION=2.6.100.51363
ARG OS_REVESION=bionic1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    #### Base utilities ####
    logrotate \
    #### Core dependencies ####
    librocksdb-dev \
    libzmq5 \
    #### SGX installer dependencies ####
    make libcurl4 libssl1.1 libprotobuf10 systemd-sysv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /root

# Must create /etc/init or enclave-common install will fail
RUN mkdir /etc/init && \
    mkdir sgx

##### Install SGX Binaries ######
COPY sgx_bins/libsgx-enclave-common_${SGX_VERSION}-${OS_REVESION}_amd64.deb ./sgx
COPY sgx_bins/libsgx-urts_${SGX_VERSION}-${OS_REVESION}_amd64.deb ./sgx

RUN dpkg -i ./sgx/libsgx-enclave-common_${SGX_VERSION}-${OS_REVESION}_amd64.deb && \
    dpkg -i ./sgx/libsgx-urts_${SGX_VERSION}-${OS_REVESION}_amd64.deb

ADD https://download.01.org/intel-sgx/linux-2.6/ubuntu18.04-server/sgx_linux_x64_sdk_${SGX_VERSION}.bin ./sgx/

RUN chmod +x ./sgx/sgx_linux_x64_sdk_${SGX_VERSION}.bin
RUN echo -e 'no\n/opt' | ./sgx/sgx_linux_x64_sdk_${SGX_VERSION}.bin && \
    echo 'source /opt/sgxsdk/environment' >> /root/.bashrc && \
    rm -rf ./sgx/*

##### Done Install SGX Binaries

# TBD: SGX Driver?

# Add env variable for dynamic linking of rocksdb
# (see https://github.com/rust-rocksdb/rust-rocksdb/issues/217)
ENV ROCKSDB_LIB_DIR=/usr/local/lib
ENV LD_LIBRARY_PATH=/opt/intel/libsgx-enclave-common/aesm
ENV PYTHONUNBUFFERED=1

RUN mkdir -p $HOME/.enigma

