#!/bin/bash

set -eu

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

case "${1:-}" in
  'postgres-slave' )
    set -- run-postgresql-slave.sh "${@:2}"
  ;;
  'postgres' | 'postgres-master' )
    set -- run-postgresql-master.sh "${@:2}"
  ;;
esac

exec "$@"
