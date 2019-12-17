# Using a debugger while working with `docker-compose`

## Prerequisites

```bash
sudo apt install docker.io
git clone git@github.com:enigmampc/docker-environment.git
cd docker-environment
```

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

(For further reading see: https://www.jetbrains.com/help/webstorm/run-debug-configuration-node-js-remote-debug.html)

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

(For further reading see: https://blog.risingstack.com/how-to-debug-a-node-js-app-in-a-docker-container/)
