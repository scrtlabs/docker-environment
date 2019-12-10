const compose = require('docker-compose');
// const { spawn } = require('child_process')
const path = require('path');

function runAsync(test_name) {
    return new Promise(async (resolve, reject) => {
        const options = {cwd: path.join("/home/avishai/CLionProjects/docker-environment/"), log: true};
        await compose.upAll(options)
            .then(
                () => {
                    console.log('up succeeded')
                },
                err => {
                    console.log('something went wrong:', err.message);
                    reject(err);
                }
            );

        let command_arg = 'sleep 30s; ' +
            'yarn test:integration test/integrationTests/02_deploy_factorization.spec.js; ' +
            'yarn test:integration test/integrationTests/' + test_name;
        await compose.exec('client', ['/bin/bash', '-c', command_arg], options).then(
            () => {
                console.log('test succeeded')
            },
            err => {
                console.log('something went wrong:', err.message)
            }
        );
        await compose.down(options)
            .then(
                () => {
                    console.log('done')
                },
                err => {
                    console.log('something went wrong:', err.message);
                    reject(err);
                }
            );
        resolve();
    });
}


runAsync('91_simultaneous_multi_gateways.spec.js').then(()=>{
    console.log("Finished first run");
    runAsync('91_simultaneous_multi_gateways_reverse.spec.js');
});
