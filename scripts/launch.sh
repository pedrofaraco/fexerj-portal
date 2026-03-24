#!/usr/bin/env bash
# launch.sh — Launch a fresh FEXERJ Portal instance on EC2.
#
# Usage:
#   bash scripts/launch.sh prod     # production (master branch)
#   bash scripts/launch.sh uat      # UAT (develop branch)
#
# Run from your laptop whenever you need the portal.
# The portal will be live at the configured domain in ~8 minutes.
#
# Prerequisites (one-time setup — see CONTRIBUTING.md):
#   1. Elastic IP allocated per environment and domain A records pointing to them
#   2. SSM parameters stored under /fexerj/prod/* and /fexerj/uat/*
#   3. IAM role fexerj-ec2-role created with AmazonSSMReadOnlyAccess
#   4. Security group allowing inbound 22, 80, 443
#   5. scripts/launch.conf filled in from scripts/launch.conf.example
#
# To destroy the instance when done:
#   bash scripts/terminate.sh [uat]

set -euo pipefail

ENV="${1:-}"
[[ "$ENV" == "prod" || "$ENV" == "uat" ]] || { echo "[ERROR] Usage: $0 <prod|uat>" >&2; exit 1; }

export AWS_PROFILE="fexerj"

CONFIG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/launch.conf"
STATE_FILE="/tmp/fexerj-${ENV}-instance-id"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

# ── Load configuration ─────────────────────────────────────────────────────────

[[ -f "$CONFIG_FILE" ]] || error "Config file not found: ${CONFIG_FILE}. Copy scripts/launch.conf.example to scripts/launch.conf and fill it in."
# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [[ "$ENV" == "prod" ]]; then
    REGION="${PROD_REGION:?launch.conf is missing PROD_REGION}"
    AMI_ID="${PROD_AMI_ID:?launch.conf is missing PROD_AMI_ID}"
    INSTANCE_TYPE="${PROD_INSTANCE_TYPE:?launch.conf is missing PROD_INSTANCE_TYPE}"
    SECURITY_GROUP="${PROD_SECURITY_GROUP:?launch.conf is missing PROD_SECURITY_GROUP}"
    ELASTIC_IP_ALLOC="${PROD_ELASTIC_IP_ALLOC:?launch.conf is missing PROD_ELASTIC_IP_ALLOC}"
    IAM_PROFILE="${PROD_IAM_PROFILE:?launch.conf is missing PROD_IAM_PROFILE}"
    DOMAIN="${PROD_DOMAIN:?launch.conf is missing PROD_DOMAIN}"
    BRANCH="master"
    SSM_PREFIX="/fexerj/prod"
else
    REGION="${UAT_REGION:?launch.conf is missing UAT_REGION}"
    AMI_ID="${UAT_AMI_ID:?launch.conf is missing UAT_AMI_ID}"
    INSTANCE_TYPE="${UAT_INSTANCE_TYPE:?launch.conf is missing UAT_INSTANCE_TYPE}"
    SECURITY_GROUP="${UAT_SECURITY_GROUP:?launch.conf is missing UAT_SECURITY_GROUP}"
    ELASTIC_IP_ALLOC="${UAT_ELASTIC_IP_ALLOC:?launch.conf is missing UAT_ELASTIC_IP_ALLOC}"
    IAM_PROFILE="${UAT_IAM_PROFILE:?launch.conf is missing UAT_IAM_PROFILE}"
    DOMAIN="${UAT_DOMAIN:?launch.conf is missing UAT_DOMAIN}"
    BRANCH="develop"
    SSM_PREFIX="/fexerj/uat"
fi

info "Environment : ${ENV} (branch: ${BRANCH})"

# ── User data (runs as root on the EC2 instance at boot) ──────────────────────

USER_DATA=$(cat <<USERDATA
#!/bin/bash
set -euo pipefail

REGION=\$(curl -sf http://169.254.169.254/latest/meta-data/placement/region)
SSM_PREFIX="${SSM_PREFIX}"

DOMAIN=\$(aws ssm get-parameter \
    --region "\$REGION" --name "\${SSM_PREFIX}/domain" \
    --query Parameter.Value --output text)

PORTAL_USER=\$(aws ssm get-parameter \
    --region "\$REGION" --name "\${SSM_PREFIX}/user" \
    --with-decryption --query Parameter.Value --output text)

PORTAL_PASSWORD=\$(aws ssm get-parameter \
    --region "\$REGION" --name "\${SSM_PREFIX}/password" \
    --with-decryption --query Parameter.Value --output text)

export DOMAIN PORTAL_USER PORTAL_PASSWORD

git clone --branch "${BRANCH}" https://github.com/pedrofaraco/fexerj-portal.git /home/ubuntu/fexerj-portal
cd /home/ubuntu/fexerj-portal
bash scripts/setup.sh
USERDATA
)

# ── Launch ────────────────────────────────────────────────────────────────────

info "Launching EC2 instance (${INSTANCE_TYPE})..."
INSTANCE_ID=$(aws ec2 run-instances \
    --region "$REGION" \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --security-group-ids "$SECURITY_GROUP" \
    --iam-instance-profile Name="$IAM_PROFILE" \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=fexerj-portal-${ENV}}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "$INSTANCE_ID" > "$STATE_FILE"
info "Instance ID : ${INSTANCE_ID}"

info "Waiting for instance to be running..."
aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

info "Attaching Elastic IP..."
aws ec2 associate-address \
    --region "$REGION" \
    --instance-id "$INSTANCE_ID" \
    --allocation-id "$ELASTIC_IP_ALLOC" \
    --output text > /dev/null

echo ""
echo "Instance is running. Setup is happening in the background (~8 min)."
echo "Portal will be live at: https://${DOMAIN}"
echo ""
echo "When done, destroy the instance:"
echo "  bash scripts/terminate.sh ${ENV}   # destroys this instance"
