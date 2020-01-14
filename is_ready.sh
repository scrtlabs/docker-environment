#!/bin/bash

REGISTERED_WORKERS_IN_KM=$(
    docker-compose logs --tail 1000 km |
        grep -P 'get_active_workers|Confirmed epoch with worker params' |
        tail -1 |
        grep -Poi '0x[a-f0-9]+' |
        sort -u |
        wc -l
)

if [[ "$REGISTERED_WORKERS_IN_KM" -eq 0 ]]; then
    exit 1
fi

exit 0
