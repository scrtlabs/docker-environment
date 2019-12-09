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

clone-salad:
	${salad}

build:
	cd worker; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
	cd worker; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f 02_core_and_p2p.Dockerfile -t enigmampc/worker_${ext}:latest .
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:latest .
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:latest .
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd client; docker build -f client.Dockerfile -t enigmampc/client:latest .

build-km:
	cd worker; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:latest .

build-contract:
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:latest .

build-worker:
	cd worker; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
	cd worker; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f 02_core_and_p2p.Dockerfile -t enigmampc/worker_${ext}:latest .

build-client:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .
	cd client; docker build -f client.Dockerfile -t enigmampc/client:latest .

build-salad-operator:
	cd salad/operator; docker build -f salad_client.Dockerfile -t enigma_salad_client .

build-salad-client:
	cd salad/client; docker build -f operator.Dockerfile -t enigma_salad_operator .
