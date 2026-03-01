#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-Wi-Fi}"

networksetup -setdnsservers "$SERVICE" 1.1.1.1 1.0.0.1 8.8.8.8 8.8.4.4
echo "dns_mode=FAST service=$SERVICE"
networksetup -getdnsservers "$SERVICE"

