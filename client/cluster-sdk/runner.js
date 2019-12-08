const {
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
    setSgxMode,
    createEnvironment,
    deleteEnvironment,
    recreateEnvironment,
    createBootstraps,
} = require('./index');
const { argv } = require('yargs');
const log = console;





async function run() {
    const namespace = 'app';
    // const sgxMode = SgxModes.SW;
    // await setSgxMode({ namespace, sgxMode });
    // await deleteEnvironment({ namespace });
    //await createEnvironment({ namespace });
    // await createBootstraps({ namespace });
    await scaleWorkers({ namespace, targetNum: 25 });
    // const namespaces = await getNamespaces();
    // const pods = await getPods({ namespace });
    // const deployments = await getDeployments({ namespace });
    //const services = await getServices({ namespace });
    // yaml.safeLoad()
    // log.info(deployments);
    //const index = await getNextWorkerIndex({ namespace });
    //log.info(index);
    //const x = await createWorkerInstance({ namespace, index });
    //log.info(await getNumberOfWorkers({ namespace }));
   
    // await deleteEnvironment({ namespace });
    //await deleteWorker({ namespace, index: 5 });
    //await restartWorker({ namespace, index: 1});
    // await restartKeyManagement({ namespace });
    //await turnOnKeyManagement({ namespace });
    //log.info(await getStatus({ namespace}));
    // const str = await execOnPod({ namespace, pod: 'worker-8-7597df945d-hnw7h', cmd: 'cat ./p2p/config/k8s_config.json'});
    //const o = await getApplicationInternalConfigFile({ namespace, name: Applications.KM })
    //log.info(o);
  //  await turnOffWorkers({ namespace, shouldDeleteService: true });
    //await turnOnKeyManagement({ namespace });
}

run()
    .then(() => log.info(`Completed Successfully`))
    .catch((e) => log.error(`Completed with error`, e));