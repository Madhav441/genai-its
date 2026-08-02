#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/compose.blue-green.yml"
NGINX_DIR="${SCRIPT_DIR}/nginx"

cleanup() {
  docker compose -f "${COMPOSE_FILE}" down --volumes --remove-orphans
}
trap cleanup EXIT

cp "${NGINX_DIR}/blue.conf.template" "${NGINX_DIR}/active.conf"

docker compose -f "${COMPOSE_FILE}" config
docker compose -f "${COMPOSE_FILE}" up --detach --build

for attempt in $(seq 1 60); do
  active_slot="$(curl --fail --silent http://localhost:8080/deployment-slot || true)"
  if [[ "${active_slot}" == "blue" ]]; then
    break
  fi
  if [[ "${attempt}" == "60" ]]; then
    echo "Blue deployment did not become ready."
    docker compose -f "${COMPOSE_FILE}" ps
    docker compose -f "${COMPOSE_FILE}" logs
    exit 1
  fi
  sleep 5
done

curl --fail --silent http://localhost:8080/_stcore/health
echo
echo "Initial blue deployment: PASS"

bash "${SCRIPT_DIR}/switch-slot.sh" green
curl --fail --silent http://localhost:8080/_stcore/health
echo
echo "Switch to green: PASS"

bash "${SCRIPT_DIR}/switch-slot.sh" blue
curl --fail --silent http://localhost:8080/_stcore/health
echo
echo "Rollback to blue: PASS"

docker compose -f "${COMPOSE_FILE}" ps
