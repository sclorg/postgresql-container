#!/bin/bash

shopt -s nullglob

cat >> "$PGDATA/postgresql.conf" <<EOF

# Custom extending configuration
EOF

extending_cfg_dir="${APP_DATA}/src/postgresql-config"

for conf in "$extending_cfg_dir"/*.conf; do
    echo include \'${conf}\' >> $PGDATA/postgresql.conf
done
