core = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_core.Dockerfile -t gitclone_core .
km = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_core.Dockerfile -t gitclone_core .
contract = cd contract; docker build --build-arg branch=${BRANCH} -f gitclone_contract.Dockerfile -t gitclone_contract .
p2p = cd worker; docker build --build-arg branch=${BRANCH} -f gitclone_p2p.Dockerfile -t gitclone_p2p .
client = cd client; docker build --build-arg branch=${BRANCH} -f gitclone_integration.Dockerfile -t gitclone_integration .
salad = cd salad; docker build --build-arg branch=${BRANCH} -f gitclone_salad.Dockerfile -t gitclone_salad .

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

.PHONY: clone-all
clone-all:
	${core}
	${p2p}
	${contract}
	${client}
	${salad}

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

.PHONY: clone-client-solo
clone-client-solo:
	${client}

.PHONY: clone-salad
clone-salad:
	${salad}

.PHONY: build
build: build-worker build-km build-contract build-client build-salad-operator build-salad-client

.PHONY: build-enigma-common
build-enigma-common:
	cd common_scripts; docker build -f common.Dockerfile -t enigma_common .

.PHONY: build-km
build-km: build-enigma-common
	cd km; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f km.Dockerfile -t enigmampc/key_management_${ext}:${DOCKER_TAG} .

.PHONY: build-contract
build-contract: build-enigma-common
	cd contract; docker build -f contract.Dockerfile -t enigmampc/contract:${DOCKER_TAG} .

.PHONY: build-worker
build-worker: build-enigma-common
	cd worker; docker build --build-arg DEBUG=${DEBUG} --build-arg SGX_MODE=${SGX_MODE} -f worker.Dockerfile -t enigmampc/worker_${ext}:${DOCKER_TAG} .

.PHONY: build-runtime-base
build-runtime-base:
	cd worker; docker build -f runtime_base.Dockerfile -t enigmampc/core-runtime-base:${DOCKER_TAG} .

.PHONY: build-compile-base
build-compile-base:
	cd worker; docker build -f compile_base.Dockerfile -t enigmampc/core-compile-base:${DOCKER_TAG} .

.PHONY: build-client
build-client: build-enigma-common
	cd client; docker build -f client.Dockerfile --build-arg DOCKER_TAG=${DOCKER_TAG} -t enigmampc/client:${DOCKER_TAG} .

.PHONY: build-salad-operator
build-salad-operator: build-enigma-common clone-core
	cd salad/operator; docker build -f operator.Dockerfile -t enigmampc/salad_operator:${DOCKER_TAG} .

.PHONY: build-salad-client
build-salad-client:
	cd salad/client; docker build -f salad_client.Dockerfile -t enigmampc/salad_client:${DOCKER_TAG} .

TESTS=./tests/
SRC = ./common_scripts/enigma_docker_common/ ./km/scripts/ ./contract/scripts/ ./client/scripts/ ./worker/scripts/
check:
	## No unused imports, no undefined vars, no line length
	flake8 --exclude __init__.py --count --exit-zero --max-line-length=127 --statistics --max-complexity 10 $(SRC)

pylint:

	pylint --rcfile .pylintrc $(SRC)


typecheck:

	mypy ./common_scripts/enigma_docker_common/
	mypy ./km/scripts
	mypy ./contract/scripts
	mypy ./client/scripts
	mypy ./worker/scripts

test:

	python -m pytest -v $(TESTS)

coverage:

	python -m pytest --cov src --cov-report term-missing $(TESTS)

prcheck:

	check pylint coverage

safety:

	safety check
