#!/usr/bin/env bash
# terminate.sh — Destroy a running FEXERJ Portal EC2 instance.
#
# Usage:
#   bash scripts/terminate.sh prod     # production
#   bash scripts/terminate.sh uat      # UAT

set -euo pipefail

ENV="${1:-}"
[[ "$ENV" == "prod" || "$ENV" == "uat" ]] || { echo "[ERROR] Usage: $0 <prod|uat>" >&2; exit 1; }

export AWS_PROFILE="fexerj"

CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/launch.conf"
STATE_FILE="/tmp/fexerj-${ENV}-instance-id"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

[[ -f "$CONFIG_FILE" ]] || error "Config file not found: ${CONFIG_FILE}."
# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [[ "$ENV" == "prod" ]]; then
    REGION="${PROD_REGION:?launch.conf is missing PROD_REGION}"
else
    REGION="${UAT_REGION:?launch.conf is missing UAT_REGION}"
fi

[[ -f "$STATE_FILE" ]] || error "No instance ID found at ${STATE_FILE}. Was launch.sh run for ${ENV}?"
INSTANCE_ID=$(cat "$STATE_FILE")

info "Terminating ${ENV} instance ${INSTANCE_ID}..."
aws ec2 terminate-instances --region "$REGION" --instance-ids "$INSTANCE_ID" --output text > /dev/null

rm -f "$STATE_FILE"
info "Done. Instance ${INSTANCE_ID} is being terminated."
info "The Elastic IP remains allocated and attached to your domain."
