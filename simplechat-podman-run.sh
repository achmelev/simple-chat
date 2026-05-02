#!/usr/bin/env bash
podman run -it --rm \
    -v "$(pwd)":/workdir \
    -e SC_LLM_URL \
    -e SC_API_KEY \
    -e SC_MODEL \
    achmelev/simplechat
