#!/bin/bash

cd src/frontend \
    && npm install \
    && npm run dev:docker &
make backend
