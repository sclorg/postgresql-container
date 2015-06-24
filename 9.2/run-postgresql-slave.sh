#!/bin/bash

source ${HOME}/common.sh

function initialize_replica() {
  echo "initialize replica called"
  check_env_vars
  #check_env_vars_for_replica
  cd /tmp
  pwd
  ls -al
  ps ax
  cat >> ".pgpass" <<-EOF
  *:*:*:*:${POSTGRESQL_PASSWORD}
  EOF
  chmod 0600 .pgpass
  export PGPASSFILE=/tmp/.pgpass
  rm -rf $PGDATA/*
  chmod 0700 $PGDATA
  pg_basebackup -x --no-password --pgdata $PGDATA --host=$POSTGRESQL_MASTER --port=5432 -U $POSTGRESQL_USER
  # PostgreSQL recovery configuration.
  cat >> "$PGDATA/recovery.conf" <<-EOF

    # Custom OpenShift recovery configuration:
    include '../openshift-custom-recovery.conf'
EOF

  pg_ctl -w start

  cat $PGDATA/pg_log/*

  pg_ctl stop
}

generate_postgresql_config
generate_passwd_file

envsubst < ${POSTGRESQL_RECOVERY_FILE}.template > ${POSTGRESQL_RECOVERY_FILE}
initialize_replica

unset_env_vars
exec "$@"