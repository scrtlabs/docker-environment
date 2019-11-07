core = cd core; docker build --build-arg branch=${BRANCH} -f clone_core.Dockerfile -t gitclone_core .
km = cd core; docker build --build-arg branch=${BRANCH} -f clone_core.Dockerfile -t gitclone_core .
contract = cd contract; docker build --build-arg branch=${BRANCH} -f clone_contract.Dockerfile -t gitclone_contract .
p2p = cd core; docker build --build-arg branch=${BRANCH} -f clone_p2p.Dockerfile -t gitclone_p2p .

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
	# ${km}
	${contract}

clone-core:
	${core}

clone-p2p:
	${p2p}

clone-km:
	${km}

clone-contract:
	${contract}

build:
	cd core; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
	cd core; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f 02_core_and_p2p.Dockerfile -t enigmampc/worker_${ext}:latest .
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:latest .
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:latest .

build-km:
	cd core; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:latest .

build-contract:
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:latest .

build-worker:
	cd core; docker build --build-arg DEBUG=${DEBUG} -f 01_core_base.Dockerfile -t enigmampc/core-base:latest .
	cd core; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f 02_core_and_p2p.Dockerfile -t enigmampc/worker_${ext}:latest .