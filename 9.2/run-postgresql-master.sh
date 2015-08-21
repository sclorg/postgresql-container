#!/bin/bash

set -eu

source ${HOME}/common.sh

check_env_vars

generate_postgresql_config
generate_passwd_file

if [ ! -f "$PGDATA/postgresql.conf" ]; then
  initialize_database
  cat >> "$PGDATA/pg_hba.conf" <<EOF

# Allow replication connections from all hosts.
host replication all all md5
EOF
  # FIXME: ^^^ only allowing replication connections from specific hosts
  #            would be a nice-to-have.
fi

pg_ctl -w start
set_passwords
pg_ctl stop

unset_env_vars
exec postgres "$@"
