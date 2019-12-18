#!/bin/bash

# Content taken from https://github.com/Azure/aks-engine/blob/master/parts/k8s/cloud-init/artifacts/cse_install.sh
PACKAGES="make gcc dkms"
apt-get -y install $PACKAGES

FILENAME="sgx_linux_x64_driver_1.12_c110012.bin"
SGX_DRIVER_URL="https://download.01.org/intel-sgx/dcap-1.2/linux/dcap_installers/ubuntuServer18.04/$FILENAME"
wget $SGX_DRIVER_URL
chmod a+x $FILENAME
./$FILENAME 
rm -f $FILENAME