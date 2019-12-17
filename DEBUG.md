# Using a debugger while working with `docker-compose`

## Prerequisites

```bash
sudo apt install docker.io
git clone git@github.com:enigmampc/docker-environment.git
cd docker-environment
```

## enigma-p2p

Go to [gitclone_p2p.Dockerfile](/worker/gitclone_p2p.Dockerfile).

1. `ARG repo_src`:
   - Set `repo_src` with the local path of `enigma-p2p` on your filesystem, e.g. `ARG repo_src=$HOME/workspace/enigma-p2p`.
2. `ARG branch`:
   - Remove the `branch` argument and `--branch ${branch}`, or set it to your desired local branch.
   - By default `branch` is set to the local checked-out branch of `repo_src`.
   - If `repo_src` is remote then the default branch is probably master.
   - You can also go into the newly cloned repo and point it to a spesific commit you'd like to debug (using `git chechout`).

(On debugging nodejs inside a container see: https://blog.risingstack.com/how-to-debug-a-node-js-app-in-a-docker-container/)

### Bootstrap
