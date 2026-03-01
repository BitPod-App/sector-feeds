#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-Wi-Fi}"

networksetup -setdnsservers "$SERVICE" Empty
echo "dns_mode=DEFAULT service=$SERVICE"
networksetup -getdnsservers "$SERVICE" || true

