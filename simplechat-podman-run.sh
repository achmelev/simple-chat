#!/usr/bin/env bash
podman run -it --rm \
    -v "$(pwd)":/workdir \
    -e SC_LLM_URL \
    -e SC_API_KEY \
    -e SC_MODEL \
    -p 9090:9090 \
    achmelev/simplechat
