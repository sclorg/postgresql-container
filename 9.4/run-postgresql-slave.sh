#!/bin/bash

set -eu

source ${HOME}/common.sh

function initialize_replica() {
  echo "Initializing PostgreSQL slave ..."
  chmod 0700 $PGDATA
  export MASTER_FQDN=$(postgresql_master_addr)
  PGPASSWORD="${POSTGRESQL_MASTER_PASSWORD}" pg_basebackup -x --no-password --pgdata ${PGDATA} --host=${MASTER_FQDN} --port=5432 -U "${POSTGRESQL_MASTER_USER}"

  # PostgreSQL recovery configuration.
  envsubst < ${POSTGRESQL_RECOVERY_FILE}.template > ${POSTGRESQL_RECOVERY_FILE}
  cat >> "$PGDATA/recovery.conf" <<EOF

# Custom OpenShift recovery configuration:
include '${POSTGRESQL_RECOVERY_FILE}'
EOF
}

check_env_vars
generate_passwd_file
generate_postgresql_config

initialize_replica

unset_env_vars
exec postgres "$@"
