const _ = require('lodash');
const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const { argv } = require('yargs');

const { sleep } = require('./utils');
const {
    createNamespace,
    getNamespaces,
    deleteNamespace,
    createDeployment,
    getDeployments,
    deleteDeployment,
    createService,
    getServices,
    deleteService,
    getPods,
    deletePod,
} = require('./k8s');
const log = console;

const cacheRefreshInterval = _.toInteger(argv.cri || process.env.CACHE_REFRESH_INTERVAL || 15 * 1000);
const DEBUG = argv.debug || process.env.DEBUG || false;


const Applications = {
    'WORKER': 'WORKER',
    'BOOTSTRAPPER': 'BOOTSTRAPPER',
    'KM': 'KM',
    'CORE': 'CORE',
    'P2P': 'P2P',
    'PROXY': 'PROXY',
    'CONTRACT': 'CONTRACT'
};

const SgxModes = {
    'SW': 'SW',
    'HW': 'HW',
}

function getDeploymentName({ name, index }) {
    return index ? `${_.toLower(name)}-${index}` : `${_.toLower(name)}`;
}

function getServiceName({ name, index }) {
    return `${getDeploymentName({ name, index })}-service`;
}

function loadTemplateDeploymentFile(_app) {
    const app = _.toLower(_app);
    const path = `../k8s-configuration/deployments/${app}/${app}.yaml`;
    const arr = yaml.safeLoadAll(fs.readFileSync(path));
    return {
        dp: _.head(_.filter(arr, x => x.kind === 'Deployment')),
        svc: _.head(_.filter(arr, x => x.kind === 'Service')),
    }
}

async function getApplicationDeploymentNames({ app, namespace }) {
    const dps = await getDeployments({ namespace });
    const workerNames = _(dps)
        .map(x => x.metadata.name)
        .filter(x => _.startsWith(x, app.toLowerCase()))
        .value();
    return workerNames;
}

async function getApplicationPodName({ app, namespace }) {
    const pods = await getPods({ namespace });
    const podNames = _(pods)
        .map(x => x.metadata.name)
        .filter(x => _.startsWith(x, app.toLowerCase()))
        .value();
    return podNames;
}

async function getWorkerNames({ namespace }) {
    return getApplicationDeploymentNames({ namespace, app: Applications.WORKER })
}

async function getNumberOfWorkers({ namespace }) {
    return _.size(await getWorkerNames({ namespace }));
}

async function getNextWorkerIndex({ namespace }) {
    const workerIdxs = _(await getWorkerNames({ namespace }))
        .map(x => _.replace(x, Applications.WORKER.toLowerCase() + '-', ''))
        .map(x => _.toInteger(x))
        .value();
    let i = 0;
    do {
        i++;
    } while (_.includes(workerIdxs, i))
    return i;
}

async function createWorkerInstance({ namespace, index }) {
    const { dp: deployment, svc: service } = loadTemplateDeploymentFile(Applications.WORKER);

    const app = `${_.toLower(Applications.WORKER)}-${index}`;
    // Manipulate Service
    service.metadata.name = `${app}-service`;
    service.spec.selector.app = app;

    // Manipulate Deployment
    deployment.metadata.name = app;
    deployment.metadata.labels.app = app;
    deployment.spec.selector.matchLabels.app = app;
    deployment.spec.template.metadata.labels.app = app;

    if (DEBUG) {
        const tmpDir = fs.mkdtempSync(`${app}-`);
        fs.writeFileSync(path.join(tmpDir, 'dp.yaml'), yaml.safeDump(deployment));
        fs.writeFileSync(path.join(tmpDir, 'svc.yaml'), yaml.safeDump(service));
        return;
    }

    await createDeployment({ namespace, deployment });
    await createService({ namespace, service });
}

async function pickRandomWorkerIndex({ namespace }) {
    return _(await getWorkerNames({ namespace }))
        .map(x => _.replace(x, Applications.WORKER.toLowerCase() + '-', ''))
        .map(x => _.toInteger(x))
        .sample();
}

async function restartWorker({ namespace, index }) {
    if (!index) {
        index = await pickRandomWorkerIndex({ namespace });
        log.info(index);
    }
    const name = Applications.WORKER;
    const podName = await getApplicationPodName({ app: getDeploymentName({ name, index }), namespace });
    await deletePod({ namespace, name: podName });
}

async function deleteWorker({ namespace, index, shouldDeleteService }) {
    if (!index) {
        index = await pickRandomWorkerIndex({ namespace });
        log.info(index);
    }

    const name = Applications.WORKER;
    const dpName = getDeploymentName({ name, index });
    await deleteDeployment({ namespace, name: dpName });
    if (shouldDeleteService) {
        const svcName = getServiceName({ name, index });
        await deleteService({ namespace, name: svcName });
    }
}

async function scaleWorkers({ namespace, targetNum, shouldDeleteService }) {
    if (targetNum < 0) {
        log.warn(`scaleWorkers: Invalid targetNum value ${targetNum}`);
    }
    const currNum = await getNumberOfWorkers({ namespace });
    log.info(`Current number of workers is ${currNum}`);
    if (currNum < targetNum) {
        for (let i = 0; i < targetNum - currNum; i++) {
            const index = await getNextWorkerIndex({ namespace })
            await createWorkerInstance({ namespace, index });
        }
    } else if (targetNum < currNum) {
        for (let i = 0; i < currNum - targetNum; i++) {
            await deleteWorker({ namespace, shouldDeleteService });
        }
    }
}

async function getStatus({ namespace, fromCache }) {
    if (fromCache) {
        const _status = Cache[namespace];
        if (_status) return _status;
    }

    const status = {};
    const names = _(await getDeployments({ namespace }))
        .map(x => x.metadata.name).value();
    const services = await getServices({ namespace });
    for (const name of names) {
        const svc = _(services).filter(x => x.metadata.name === `${name}-service`).head();
        const val = {};
        const externalIp = _.get(svc, 'status.loadBalancer.ingress[0].ip', '');
        _.set(val, 'externalIp', externalIp);
        if (_.startsWith(name, 'worker')) {
            const ethereumAddress = await getWorkerEthereumAddress({ namespace, deploymentName: name });
            _.set(val, 'ethereumAddress', ethereumAddress);
        }
        _.set(status, name, val);
    }
    return status;
}

async function turnOffWorkers({ namespace, shouldDeleteService }) {
    return scaleWorkers({ namespace, targetNum: 0, shouldDeleteService });
}

async function restartKeyManagement({ namespace }) {
    const name = Applications.KM;
    const podName = await getApplicationPodName({ app: getDeploymentName({ name }), namespace });
    await deletePod({ namespace, name: podName });
}

async function turnOnKeyManagement({ namespace }) {
    const { dp } = loadTemplateDeploymentFile(Applications.KM);
    await client.apis.apps.v1.namespaces(namespace).deployments.post({ body: dp });
}

async function turnOffApplication({ namespace, name, index, shouldDeleteService }) {
    const dpName = getDeploymentName({ name, index });
    await deleteDeployment({ namespace, name: dpName });
    if (shouldDeleteService) {
        const svcName = getServiceName({ name, index });
        await deleteService({ namespace, name: svcName });
    }
}

async function turnOffContract({ namespace, shouldDeleteService }) {
    const appName = Applications.CONTRACT;
    await turnOffApplication({ namespace, name: appName, shouldDeleteService });
}

async function turnOffKeyManagement({ namespace, shouldDeleteService }) {
    const appName = Applications.KM;
    await turnOffApplication({ namespace, name: appName, shouldDeleteService });
}

async function execOnPod({ namespace, pod, cmd }) {
    const res = await client.api.v1.namespaces(namespace).pods(pod).exec.post({
        qs: {
            command: _.split(cmd, ' '),
            stdout: true,
            stderr: true
        }
    })
    return res.body;
}

async function getApplicationInternalConfigFile({ namespace, name, index, subPath }) {
    const pod = await getApplicationPodName({ app: getDeploymentName({ name, index }), namespace });
    const cmd = subPath ? `cat ./${subPath}/config/k8s_config.json` : `cat ./config/k8s_config.json`;
    const str = await execOnPod({ namespace, pod, cmd });
    return JSON.parse(str);
}

async function getWorkerEthereumAddress({ namespace, deploymentName }) {
    const pod = await getApplicationPodName({ app: deploymentName, namespace });
    const cmd = `cat ./p2p/id_rsa.pub`;
    const str = await execOnPod({ namespace, pod, cmd });
    return str;
}

async function stopWorkerProcess({ namespace, index, name }) {
    if (!index) {
        index = await pickRandomWorkerIndex({ namespace });
        log.info(index);
    }
    const app_name = name ? name : Applications.WORKER;
    const pod = await getApplicationPodName({ app: getDeploymentName({ name: app_name, index }), namespace });
    let cmd = `supervisorctl stop p2p`;
    await execOnPod({ namespace, pod, cmd });
    cmd = `supervisorctl stop core`;
    await execOnPod({ namespace, pod, cmd });
}

async function startWorkerProcess({ namespace, index, name}) {
    if (!index) {
        index = await pickRandomWorkerIndex({ namespace });
        log.info(index);
    }
    const app_name = name ? name : Applications.WORKER;
    const pod = await getApplicationPodName({ app: getDeploymentName({ name: app_name, index }), namespace });
    let cmd = `supervisorctl start core`;
    await execOnPod({ namespace, pod, cmd });
    cmd = `supervisorctl start p2p`;
    await execOnPod({ namespace, pod, cmd });
}

const Cache = {};
const Intervals = {};

async function enableCache({ namespace }) {
    if (Intervals[namespace]) {
        log.info(`enableCache: cache already initialized for namespace ${namespace}`);
        return;
    }
    const handle = setInterval(async () => {
        statusCache[namespace] = await getStatus();
    }, cacheRefreshInterval);
    Intervals[namespace] = handle;
}

function disableCache({ namespace }) {
    const handle = Intervals[namespace];
    if (handle) {
        clearInterval(handle);
    }
}

// Hashmap of namespace -> sgx mode (HW/SW), default is SW
const SgxModeStatus = {};
function setSgxMode({ namespace, sgxMode }) {
    const mode = _.trim(_.toUpper(sgxMode));
    if (mode === SgxModes.HW) {
        _.set(SgxModeStatus, namespace, SgxModes.HW);
    } else {
        _.set(SgxModeStatus, namespace, SgxModes.SW);
    }
}

function getSgxMode({ namespace }) {
    return SgxModeStatus[namespace] || SgxModes.SW;
}

function manipulateDeploymentDueSgxMode({ namespace, deployment }) {
    const DEFAULT_IMAGE_SGX_MODE = '_sw:';
    const currentImage = deployment.spec.template.spec.containers[0].image;
    if (_.includes(currentImage, DEFAULT_IMAGE_SGX_MODE)) {
        const newImage = _.replace(currentImage, DEFAULT_IMAGE_SGX_MODE, _.toLower(`_${getSgxMode({ namespace })}:`));
        deployment.spec.template.spec.containers[0].image = newImage;
    }

    const keyName = 'SGX_MODE';
    const env = deployment.spec.template.spec.containers[0].env;
    const index = _.findIndex(env, x => x.name === keyName);
    if (index > 0) {
        env[index] = { name: keyName, value: getSgxMode({ namespace })};
        deployment.spec.template.spec.containers[0].env = env;
    }


    let i = 9;
    return deployment;
}

// Deploys contract, KM and Bootstrappers
async function createEnvironment({ namespace }) {
    await createNamespace({ namespace });

    const contractManifests = loadTemplateDeploymentFile(Applications.CONTRACT);
    const newContractDp = manipulateDeploymentDueSgxMode({ namespace, deployment: contractManifests.dp });
    await createDeployment({ namespace, deployment: newContractDp });
    await createService({ namespace, service: contractManifests.svc });

    const minutesToSleep = 3;
    log.info(`Sleeping for ${minutesToSleep} minutes so the contract will be up and running`);
    await sleep(minutesToSleep * 60 * 1000);

    const kmManifests = loadTemplateDeploymentFile(Applications.KM);
    const newKmDp = manipulateDeploymentDueSgxMode({ namespace, deployment: kmManifests.dp });
    await createDeployment({ namespace, deployment: newKmDp });
    await createService({ namespace, service: kmManifests.svc });

    // TODO multi!!
    const btsManifests = loadTemplateDeploymentFile(Applications.BOOTSTRAPPER);
    const newBtsDp = manipulateDeploymentDueSgxMode({ namespace, deployment: btsManifests.dp });
    await createDeployment({ namespace, deployment: newBtsDp });
    await createService({ namespace, service: btsManifests.svc });
}

async function deleteEnvironment({ namespace }) {
    // Namespace will be deleted, all sub-objects will be cascaded
    return deleteNamespace({ namespace });
}

module.exports = {
    Applications,
    SgxModes,
    turnOffWorkers,
    scaleWorkers,
    restartWorker,
    deleteWorker,
    getNumberOfWorkers,
    turnOnKeyManagement,
    turnOffKeyManagement,
    restartKeyManagement,
    getStatus,
    getApplicationInternalConfigFile,
    startWorkerProcess,
    stopWorkerProcess,
    createEnvironment,
    deleteEnvironment,
    setSgxMode,
    getSgxMode,
};

