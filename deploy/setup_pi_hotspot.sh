#!/usr/bin/env bash
#
# setup_pi_hotspot.sh — turn this Raspberry Pi into the Sahar-Connect edge node's
# own WiFi access point.
#
#   wlan0  -> broadcasts SSID "Sahar-Connect-Emergency" (phones connect here)
#   eth0   -> stays as-is (internet + your SSH session are NOT touched)
#
# Phones that join the hotspot get an IP automatically (NetworkManager runs DHCP
# via `ipv4.method shared`) and can reach the dashboard at the Pi's hotspot IP
# (10.42.0.1 by default), with NO internet required for the dispatch logic.
#
# This script only CREATES the connection profile (autoconnect off), so running
# it will NOT kick you off WiFi. You bring it live deliberately (see the end).
#
set -euo pipefail

SSID="Sahar-Connect-Emergency"
PASSWORD="alquaa2026"     # must be >= 8 chars. For an OPEN network, see note below.
CON="sahar-hotspot"
IFACE="wlan0"

echo "[hotspot] (re)creating AP profile '$CON' on $IFACE  (SSID: $SSID)"

# Re-runnable: remove any previous version first.
sudo nmcli connection delete "$CON" >/dev/null 2>&1 || true

sudo nmcli connection add type wifi ifname "$IFACE" con-name "$CON" \
    autoconnect no ssid "$SSID"

sudo nmcli connection modify "$CON" \
    802-11-wireless.mode ap \
    802-11-wireless.band bg \
    ipv4.method shared \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "$PASSWORD" \
    connection.autoconnect-priority 10

echo
echo "[hotspot] profile created. SSID: $SSID   password: $PASSWORD"
echo
echo "  GO LIVE (drops wlan0 off home WiFi; eth0 + SSH stay up):"
echo "      sudo nmcli connection up $CON"
echo
echo "  STOP (return wlan0 to home WiFi):"
echo "      sudo nmcli connection down $CON"
echo
echo "  MAKE IT START ON BOOT (after you've tested it once):"
echo "      sudo nmcli connection modify $CON connection.autoconnect yes"
echo
echo "  OPEN network instead (no password — easiest for judges to join):"
echo "      sudo nmcli connection modify $CON wifi-sec.key-mgmt none && sudo nmcli connection up $CON"
