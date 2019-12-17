# Using a debugger while working with `docker-compose`

## Prerequisites

```bash
sudo apt install -y docker.io
git clone git@github.com:enigmampc/docker-environment.git
cd docker-environment
```

## enigma-core

Build a docker image from the local version of `enigma-core`. E.g.:

```bash
make build-local-core path=$HOME/workspace/enigma-core
```

### CLion

Sources:

- https://github.com/apache/incubator-teaclave-sgx-sdk/wiki/Debugging-a-local-Rust-SGX-enclave-in-docker-with-sgx-gdb
- https://medium.com/nearprotocol/remote-development-and-debugging-of-rust-with-clion-39c38ced7cc1

## enigma-p2p

Build a docker image from the local version of `enigma-p2p`. E.g.:

```bash
make build-local-p2p path=$HOME/workspace/enigma-p2p
```

### WebStorm

1. Go to `Run` -> `Edit Configurations` -> `+` (Alt+Insert) -> `Attach to Node.js/Chrome`.
2. `Host`: Set to `localhost`.
3. `Port`: Set to `9229` for bootstrap or `9230` for worker.
4. `Attach to`: Select `Chrome or Node.js > 6.3 started with --inspect`.
5. `Remote URLs of local files`: Set `/root/p2p` for the root folder (`/path/to/enigma-p2p`).
6. `Ok`.

Now while `docker-compose up` is running you can run the debugger with this new configuration.

Sources:

- https://www.jetbrains.com/help/webstorm/run-debug-configuration-node-js-remote-debug.html

### vscode

Add this to `.vscode/launch.json` under `configurations`:

```json
{
  "type": "node",
  "request": "attach",
  "name": "Attach to Remote",
  "address": "localhost",
  "port": 9229,
  "localRoot": "${workspaceFolder}",
  "remoteRoot": "/root/p2p",
  "skipFiles": ["<node_internals>/**"]
}
```

(`port`: Set to `9229` for bootstrap or `9230` for worker.)

Now while `docker-compose up` is running in the debug menu (Ctrl+Shift+D) choose `Attch to Remote` and press `F5`.

Sources:

- https://blog.risingstack.com/how-to-debug-a-node-js-app-in-a-docker-container/

## enigma-p2p-monitor

Currently `enigma-p2p-monitor` isn't a part of the `docker-environment`, so we must run it locally and make it connect to `docker-environment`.

Prerequisite in order to parse `Enigma.json`:

```bash
sudo apt install -y jq
```

Terminal 1:

```bash
cd workspace/docker-environment
docker-compose up
```

Terminal 2:

```bash
cd workspace/enigma-p2p-monitor
node main.js --bootstrap "/ip4/127.0.0.1/tcp/10300/ipfs/QmcrQZ6RJdpYuGvZqD5QEHAv6qX4BrQLJLQPQUrTrzdcgm" --enigma-contract-address $(curl -s 'http://localhost:8081/contract/address?name=enigmacontract.txt' | tr -d \") --enigma-contract-json-path <(curl -s 'http://localhost:8081/contract/abi?name=Enigma.json' | jq '. | fromjson')
```

When debugging:

- Get the `--enigma-contract-address` arg with `curl -s 'http://localhost:8081/contract/address?name=enigmacontract.txt' | tr -d \"`.
- Get the `--enigma-contract-json-path` arg with `curl -s 'http://localhost:8081/contract/abi?name=Enigma.json' | jq '. | fromjson' > Enigma.json` and use like `--enigma-contract-json-path Enigma.json`.
