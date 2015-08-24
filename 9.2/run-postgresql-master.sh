#!/bin/bash

set -eu

source ${HOME}/common.sh

check_env_vars
generate_passwd_file
generate_postgresql_config

if [ ! -f "$PGDATA/postgresql.conf" ]; then
  initialize_database
fi

pg_ctl -w start
set_passwords
pg_ctl stop

unset_env_vars
exec postgres "$@"
