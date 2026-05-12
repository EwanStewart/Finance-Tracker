#!/bin/sh
# Publish an mDNS A record for $1.local pointing at this host's primary IPv4.
# Used by mdns-alias@.service (instance name = $1).

set -eu

IP=$(hostname -I | awk '{print $1}')
if [ -z "$IP" ]; then
    echo "No IPv4 address found via hostname -I" >&2
    exit 1
fi

exec /usr/bin/avahi-publish -a -R "$1.local" "$IP"
