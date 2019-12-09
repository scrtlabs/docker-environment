core = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_core.Dockerfile -t gitclone_core .
km = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_core.Dockerfile -t gitclone_core .
contract = cd contract; docker build --build-arg branch=${BRANCH} -f gitclone_contract.Dockerfile -t gitclone_contract .
p2p = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_p2p.Dockerfile -t gitclone_p2p .
client = cd client; docker build --build-arg branch=${BRANCH} -f gitclone_integration.Dockerfile -t gitclone_integration .
salad = cd salad; docker build --build-arg branch=${BRANCH} -f gitclone_salad.Dockerfile -t gitclone_salad .

SGX_MODE ?= HW
BRANCH ?= develop
DEBUG ?= 0

ifeq ($(SGX_MODE), HW)
	ext := hw
else ifeq ($(SGX_MODE), SW)
	ext := sw
else
$(error SGX_MODE must be either HW or SW)
endif

.PHONY: clone-all
clone-all:
	${core}
	${p2p}
	${contract}
	${client}

.PHONY: clone-core
clone-core:
	${core}

.PHONY: clone-p2p
clone-p2p:
	${p2p}

.PHONY: clone-km
clone-km:
	${km}

.PHONY: clone-contract
clone-contract:
	${contract}

.PHONY: clone-client
clone-client:
	${contract}
	${client}

.PHONY: clone-salad
clone-salad:
	${salad}

.PHONY: build
build: build-worker build-km build-contract build-client build-salad-operator build-salad-client

.PHONY: build-core-base
build-core-base:
	cd worker; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .

.PHONY: build-km
build-km: build-core-base
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:latest .

.PHONY: build-contract
build-contract:
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:latest .

.PHONY: build-worker
build-worker: build-core-base
	cd worker; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f 02_core_and_p2p.Dockerfile -t enigmampc/worker_${ext}:latest .

.PHONY: build-client
build-client:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd client; docker build -f client.Dockerfile -t enigmampc/client:latest .

.PHONY: build-salad-operator
build-salad-operator:
	cd salad/operator; docker build -f salad_client.Dockerfile -t enigma_salad_client .

.PHONY: build-salad-client
build-salad-client:
	cd salad/client; docker build -f operator.Dockerfile -t enigma_salad_operator .
