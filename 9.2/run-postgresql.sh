#!/bin/bash

set -eu

source ${HOME}/common.sh

# Data dir
if [ -O $HOME/data ]; then
  export PGDATA=$HOME/data
else
  # If current user does not own data directory
  # create a subdirectory that the user does own
  if [ ! -d $HOME/data/userdata ]; then
    mkdir $HOME/data/userdata
  fi
  export PGDATA=$HOME/data/userdata
fi

if [ "$1" == "postgresql-master" ]; then
  shift
  exec /usr/local/bin/run-postgresql-master.sh $@
fi

if [ "$1" == "postgresql-slave" ]; then
  shift
  exec /usr/local/bin/run-postgresql-slave.sh $@
fi

generate_postgresql_config
generate_passwd_file

if [ "$1" = "postgres" -a ! -f "$PGDATA/postgresql.conf" ]; then
  initialize_database
fi

unset_env_vars
exec "$@"
