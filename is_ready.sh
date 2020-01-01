#!/bin/bash

WORKERS=$(
    docker-compose ps |
        grep -P 'worker|bootstrap' |
        wc -l
)

REGISTERED_WORKERS_IN_KM=$(
    docker-compose logs --tail 1000 km |
        grep -F 'get_active_workers() =>' |
        tail -1 |
        grep -Poi '0x[a-f0-9]+' |
        sort -u |
        wc -l
)

if [[ "$WORKERS" -eq "$REGISTERED_WORKERS_IN_KM" ]]; then
    exit 0
fi

exit 1
