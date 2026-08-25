#!/usr/bin/env bash
# Headless CLI run of the Postman collection (this is the "Newman" the JD asks for).
# Requires: npm i -g newman
set -euo pipefail
newman run api/engineering-intelligence-hub.postman_collection.json \
  -e api/postman_environment.json \
  --reporters cli,json \
  --reporter-json-export api/newman-report.json
