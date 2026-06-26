#!/usr/bin/env bash
#
# setup_captive.sh — keep iOS/Android from dropping the offline hotspot.
#
# Installs a DNS override (so OS connectivity checks resolve to this Pi) plus a
# tiny port-80 responder that answers those checks with "success". The phone
# then believes the hotspot has internet and won't auto-disconnect when the
# Ethernet uplink is unplugged.
#
# EXPERIMENTAL — run on the Pi and TEST (join hotspot, unplug ethernet, confirm
# the phone stays connected). Fully reversible — see UNDO at the bottom.
#
# Note: this briefly takes the hotspot down/up to reload dnsmasq, so run it from
# an Ethernet (eth0) SSH session so you don't lose your shell.
#
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[captive] installing dnsmasq drop-in..."
sudo install -d /etc/NetworkManager/dnsmasq-shared.d
sudo cp "$DIR/dnsmasq-captive.conf" /etc/NetworkManager/dnsmasq-shared.d/sahar-captive.conf

echo "[captive] installing + starting the port-80 responder..."
sudo cp "$DIR/sahar-captive.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sahar-captive

echo "[captive] reloading the hotspot so dnsmasq picks up the new config..."
sudo nmcli connection down sahar-hotspot || true
sudo nmcli connection up sahar-hotspot

echo
echo "[captive] done. TEST NOW:"
echo "  1. Join 'Sahar-Connect-Emergency' on a phone."
echo "  2. Unplug the Ethernet cable from the Pi."
echo "  3. Confirm the phone stays on the WiFi and http://10.42.0.1:8501 still loads."
echo
echo "UNDO (if it misbehaves):"
echo "  sudo rm -f /etc/NetworkManager/dnsmasq-shared.d/sahar-captive.conf"
echo "  sudo systemctl disable --now sahar-captive"
echo "  sudo nmcli connection down sahar-hotspot && sudo nmcli connection up sahar-hotspot"
