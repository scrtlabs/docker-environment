#!/bin/bash

WORKERS=$(
    docker-compose ps |
        grep -P 'worker|bootstrap' |
        wc -l
)

if [[ "$WORKERS" -eq 0 ]]; then
    exit 1
fi

REGISTERED_WORKERS_IN_KM=$(
    docker-compose logs --tail 1000 km |
        grep -P 'get_active_workers|Confirmed epoch with worker params' |
        tail -1 |
        grep -Poi '0x[a-f0-9]+' |
        sort -u |
        wc -l
)

if [[ "$WORKERS" -ne "$REGISTERED_WORKERS_IN_KM" ]]; then
    exit 1
fi

exit 0
