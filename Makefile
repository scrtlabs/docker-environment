core = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_core.Dockerfile -t gitclone_core .
km = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_core.Dockerfile -t gitclone_core .
contract = cd contract; docker build --build-arg branch=${BRANCH} -f gitclone_contract.Dockerfile -t gitclone_contract .
p2p = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_p2p.Dockerfile -t gitclone_p2p .
client = cd client; docker build --build-arg branch=${BRANCH} -f gitclone_integration.Dockerfile -t gitclone_integration .

SGX_MODE ?= HW
BRANCH ?= develop
DEBUG ?= 0
DOCKER_TAG ?= latest

ifeq ($(SGX_MODE), HW)
	ext := hw
else ifeq ($(SGX_MODE), SW)
	ext := sw
else
$(error SGX_MODE must be either HW or SW)
endif

clone-all:
	${core}
	${p2p}
	${contract}
	${client}

clone-core:
	${core}

clone-p2p:
	${p2p}

clone-km:
	${km}

clone-contract:
	${contract}

clone-client:
	${contract}
	${client}

clone-client-solo:
	${client}

build:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd worker; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f worker.Dockerfile -t enigmampc/worker_${ext}:${DOCKER_TAG} .
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:${DOCKER_TAG} .
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:${DOCKER_TAG} .
	cd client; docker build -f client.Dockerfile --build-arg DOCKER_TAG=${DOCKER_TAG} -t enigmampc/client:${DOCKER_TAG} .

build-km:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:${DOCKER_TAG} .

build-contract:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:${DOCKER_TAG} .

build-worker:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd worker; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f worker.Dockerfile -t enigmampc/worker_${ext}:${DOCKER_TAG} .

build-runtime-base:
	cd worker; docker build -f runtime_base.Dockerfile -t enigmampc/core-runtime-base:${DOCKER_TAG} .

build-compile-base:
	cd worker; docker build -f compile_base.Dockerfile -t enigmampc/core-compile-base:${DOCKER_TAG} .

build-client:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd client; docker build -f client.Dockerfile --build-arg DOCKER_TAG=${DOCKER_TAG} -t enigmampc/client:${DOCKER_TAG} .
