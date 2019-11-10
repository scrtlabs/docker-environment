const _ = require('lodash');
const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const { argv } = require('yargs');
const { KubeConfig, Client } = require('kubernetes-client');
const Request = require('kubernetes-client/backends/request')
const log = console;

const region = argv.region || process.env.REGION || 'eastus';
const cluster = argv.cluster || process.env.CLUSTER || 'enigma-cluster';
const namespace = argv.ns || process.env.NS || 'app';
const DEBUG = argv.debug || process.env.DEBUG || false;

const kubeconfig = new KubeConfig();
const kubernetesVersion = '1.13';
kubeconfig.loadFromFile(`../k8s-deployment/_output/${cluster}/kubeconfig/kubeconfig.${region}.json`);

const client = new Client({ backend: new Request({ kubeconfig }), version: kubernetesVersion });

const Applications = {
    'WORKER': 'WORKER',
    'BOOTSTRAPPER': 'BOOTSTRAPPER',
    'KM': 'KM',
    'CORE': 'CORE',
    'P2P': 'P2P',
    'PROXY': 'PROXY',
    'CONTRACT': 'CONTRACT'
};

function getDeploymentName({ name, index }) {
    return index ? `${_.toLower(name)}-${index}` : `${_.toLower(name)}`;
}

function getServiceName({ name, index }) {
    return `${getDeploymentName({ name, index })}-service`;
}

async function getServices({ namespace }) {
    return (await client.api.v1.namespaces(namespace).services.get()).body.items;
}

async function getPods({ namespace }) {
    return (await client.api.v1.namespaces(namespace).pods.get()).body.items;
}

async function getDeployments({ namespace }) {
    return (await client.apis.apps.v1.namespaces(namespace).deployments.get()).body.items;
}

async function getNamespaces() {
    return (await client.api.v1.namespaces.get()).body.items;
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

async function createDeployment({ namespace, deployment }) {
    const name = deployment.metadata.name;
    try {
        const create = await client.apis.apps.v1.namespaces(namespace).deployments.post({ body: deployment });
        // log.info('Create:', create);
    } catch (err) {
        if (err.code !== 409) throw err;
        const replace = await client.apis.apps.v1.namespaces(namespace).deployments(name).put({ body: deployment });
        // log.info('Replace:', replace);
    }
}

async function deleteDeployment({ namespace, name }) {
    await client.apis.apps.v1.namespaces(namespace).deployments(name).delete();
}

async function createService({ namespace, service }) {
    const name = service.metadata.name;
    try {
        const create = await client.api.v1.namespaces(namespace).services.post({ body: service });
        // log.info('Create:', create);
    } catch (err) {
        if (err.code !== 409) throw err;
        const existingSvc = _(await getServices({ namespace })).filter(x => x.metadata.name === name).head();
        // ClusterIP is immutable, resourceVersion should be set
        service.spec.clusterIP = existingSvc.spec.clusterIP;
        service.metadata.resourceVersion = existingSvc.metadata.resourceVersion;
        const replace = await client.api.v1.namespaces(namespace).services(name).put({ body: service });
        // log.info('Replace:', replace);
    }
}

async function deleteService({ namespace, name }) {
    await client.api.v1.namespaces(namespace).services(name).delete();
}

async function deletePod({ namespace, name }) {
    await client.api.v1.namespaces(namespace).pods(name).delete();
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

async function getStatus({ namespace }) {
    const retVal = {};
    const names = _(await getDeployments({ namespace }))
        .map(x => x.metadata.name).value();
    const services = await getServices({ namespace });
    for (const name of names) {
        const svc = _(services).filter(x => x.metadata.name === `${name}-service`).head();
        const externalIp = _.get(svc, 'status.loadBalancer.ingress[0].ip', '')
        _.set(retVal, name, externalIp);
    }
    return retVal;
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


module.exports = {
    Applications,
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
};

