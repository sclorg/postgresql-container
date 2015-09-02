#!/bin/sh

. /usr/share/container-layer/postgresql/atomic/include.sh

chroot "${HOST}" /usr/bin/systemctl disable "${service_name}.service"
chroot "${HOST}" /usr/bin/systemctl stop "${service_name}.service"
rm -f "${HOST}/etc/systemd/system/${service_name}.service"

