Current:
![](https://github.com/enigmampc/docker-environment/workflows/CI/badge.svg)
![](https://github.com/enigmampc/docker-environment/workflows/Python%20Checking/badge.svg)

Develop:
![](https://github.com/enigmampc/docker-environment/workflows/CI/badge.svg?branch=develop)
![](https://github.com/enigmampc/docker-environment/workflows/Python%20Checking/badge.svg?branch=develop)

Master:
![](https://github.com/enigmampc/docker-environment/workflows/CI/badge.svg?branch=master)
![](https://github.com/enigmampc/docker-environment/workflows/Python%20Checking/badge.svg?branch=master)

# Welcome to the new docker environment!

# What's new?

### Major changes

+ All new docker images -- improved size and build times!
+ Core and p2p unification -- now called worker
+ More configuration -- you can now set any parameter via environment variables, or per-environment configuration
+ Scalability -- Support for up to a bazillion worker nodes!
+ Progress towards Test/Mainnet & packaging images provided to users
+ Rewritten startup scripts in Python

### Minor changes

+ Change startup of aesm_service to non-daemon mode (docker doesn't like daemon processes)
+ Supervisord now manages all image processes
+ Preparing centralized logging

## Building images

Just use the makefile to clone the repos from github:
```
make clone-all
```

``clone-all`` can take the following arguments:

Example:

```
make clone-all BRANCH=master
```

* `BRANCH` | default = develop

And build all the images: 
```
make build
```

Build can take the following arguments:

* `SGX_MODE` | default = HW
* `DEBUG` | default = 0  

Example:

```
make build SGX_MODE=SW DEBUG=0
```

The following make targets also exist:

* clone-core
* clone-p2p
* clone-km
* clone-contract
* clone-client
* build-km
* build-contract
* build-worker
* build-client

## Installation

Copy `.env.template` to `.env` and adjust any values as needed:
```
cp .env.template .env
```

Software mode:
```
docker-compose up
```

Hardware mode:
```
docker-compose -f docker-compose.yml -f docker-compose.hw.yml up
```

** Current develop is still kind of bugged, so it won't actually run all the tests successfully 

## Client Usage

The compose by default comes with a client you can use to run tests on the cluster. To use, just exec ``make test`` in the client

```
docker-compose exec client make test
```

### Set the number of workers

```
docker-compose scale worker=X
```

Be careful you have enough memory to run all those workers though!

## Manual build

### Worker

1. Clone from github both `core` and `p2p`:
```
docker build -f gitclone_core.Dockerfile -t gitclone_core .
docker build -f gitclone_p2p.Dockerfile -t gitclone_p2p .
```

Note: it's possible to change each image to pull from a branch, for example `develop`:
```
docker build -f gitclone_core.Dockerfile -t gitclone_core --build-arg branch=develop .
docker build -f gitclone_p2p.Dockerfile -t gitclone_p2p --build-arg branch=develop .
```

2. **(Optional)** Build base image:
```
docker build --build-arg DEBUG=1 --build-arg SGX_MODE=SW -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
```  

3. Build worker image:
```
docker build --build-arg SGX_MODE=SW -f 02_core_and_p2p.Dockerfile -t enigmampc/worker-minimal:latest .
``` 

#### Optional steps

+ Build custom image based off baidu image:
```
docker build -f baidu1804.Dockerfile -t baiduxlab/sgx-rust:1804-1.0.9 .
```

+ Recompile SGX binaries. Will be useful if we want to move off Ubuntu 18.04:
```
docker build -f buildSGX.Dockerfile -t buildsgx .
```

### Key Management

1. Clone from github:
```
docker build -f gitclone_km.Dockerfile -t gitclone_km .
```

Note: it's possible to change each image to pull from a branch, for example `develop`:
```
docker build -f gitclone_km.Dockerfile -t gitclone_km --build-arg branch=develop .
```

2. **(Optional)** Build base image:
```
docker build --build-arg SGX_MODE=SW -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
```  

3. Build Key Management image:
```
docker build --build-arg SGX_MODE=SW -f km.Dockerfile -t enigmampc/key_management:latest .
``` 

### Contract

1. Clone from github:
```
docker build -f gitclone_contract.Dockerfile -t gitclone_contract .
``` 

Note: it's possible to change each image to pull from a branch, for example `develop`:
```
docker build -f gitclone_contract.Dockerfile -t gitclone_contract --build-arg branch=develop .
```

2. Build Enigma-Contract image:
```
docker build --build-arg SGX_MODE=SW -f contract.Dockerfile -t enigmampc/contract:latest .
```  

### Client

1. Build `enigma_common` Docker image:
```
cd common_scripts/
docker build -f common.Dockerfile -t enigma_common .
cd ..
```

2. Clone `integration-tests` from Github:
```
cd client
docker build -f gitclone_integration.Dockerfile -t gitclone_integration .
```

Note: it's possible to change each image to pull from a branch, for example `develop`:
```
docker build -f gitclone_integration.Dockerfile -t gitclone_integration --build-arg branch=develop .
```

3. Build Client image:
```
docker build -f client.Dockerfile -t enigmampc/client:latest .
```

### Development

Clone this repository. If cloned into Pycharm you should get all the build configurations for free

Each image uses the following:

1. Dockerfile
2. Devops folder -- containing docker-level configuration
3. Scripts folder -- containing all the start-up scripts
4. Config folder -- configuration defaults, per environment 

## TODO
1. More documentation on environment variables
