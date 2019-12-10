const compose = require('docker-compose');
// const { spawn } = require('child_process')
const path = require('path');

async function run() {
    const options = {cwd: path.join("/home/avishai/CLionProjects/docker-environment/"), log: true};
    await compose.upAll(options)
        .then(
            async () => {
                console.log('up succeeded')
            },
            err => {
                console.log('something went wrong:', err.message)
            }
        );
        // // scale up to 2 workers
        // spawn('docker-compose', ['scale','worker=2'])

    let command_arg = 'sleep 30s; ' +
        'yarn test:integration test/integrationTests/02_deploy_factorization.spec.js; ' +
        'yarn test:integration test/integrationTests/91_simultaneous_multi_gateways.spec.js';
    await compose.exec('client', ['/bin/bash', '-c', command_arg] , options).then(
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
                console.log('something went wrong:', err.message)
            }
        );
}

run();
