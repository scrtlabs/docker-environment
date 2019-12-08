#!/usr/bin/env node

function execute(command) {
    const exec = require('child_process').exec

    exec(command, (err, stdout, stderr) => {
        process.stdout.write(stdout)
    })
}

execute('docker-compose up -f ../docker-compose.yml')