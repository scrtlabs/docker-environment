const { KubeConfig, Client } = require('kubernetes-client');
const Request = require('kubernetes-client/backends/request');
const _ = require('lodash');
const { argv } = require('yargs');

const region = argv.region || process.env.REGION || 'eastus';
const cluster = argv.cluster || process.env.CLUSTER || 'enigma-cluster';

const kubeconfig = new KubeConfig();
const kubernetesVersion = '1.13';
kubeconfig.loadFromFile(`../k8s-deployment/_output/${cluster}/kubeconfig/kubeconfig.${region}.json`);

const client = new Client({ backend: new Request({ kubeconfig }), version: kubernetesVersion });

async function createNamespace({ namespace }) {
    const body = {
        apiVersion: 'v1',
        kind: 'Namespace',
        metadata: {
            name: namespace
        }
    };

    try {
        const create = await client.api.v1.namespaces.post({ body });
        // log.info('Create:', create);
    } catch (err) {
        if (err.code !== 409) throw err;
        const replace = await client.api.v1.namespaces(namespace).put({ body });
    }
}

async function getNamespaces() {
    return (await client.api.v1.namespaces.get()).body.items;
}

async function deleteNamespace({ namespace }) {
    await client.api.v1.namespaces(namespace).delete();
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

async function getDeployments({ namespace }) {
    return (await client.apis.apps.v1.namespaces(namespace).deployments.get()).body.items;
}

async function deleteDeployment({ namespace, name }) {
    await client.apis.apps.v1.namespaces(namespace).deployments(name).delete();
}

async function getServices({ namespace }) {
    return (await client.api.v1.namespaces(namespace).services.get()).body.items;
}

async function createService({ namespace, service }) {
    const name = service.metadata.name;
    try {
        service.spec.clusterIP = undefined;
        service.metadata.resourceVersion = undefined;
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


async function getPods({ namespace }) {
    return (await client.api.v1.namespaces(namespace).pods.get()).body.items;
}

async function deletePod({ namespace, name }) {
    await client.api.v1.namespaces(namespace).pods(name).delete();
}


module.exports = {
    createNamespace,
    deleteNamespace,
    getNamespaces,
    createDeployment,
    getDeployments,
    deleteDeployment,
    createService,
    getServices,
    deleteService,
    getPods,
    deletePod,
};
