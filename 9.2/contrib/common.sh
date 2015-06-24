#!/bin/bash

# Configuration settings.
export POSTGRESQL_MAX_CONNECTIONS=${POSTGRESQL_MAX_CONNECTIONS:-100}
export POSTGRESQL_SHARED_BUFFERS=${POSTGRESQL_SHARED_BUFFERS:-32MB}

export POSTGRESQL_RECOVERY_FILE=$HOME/openshift-custom-recovery.conf
export POSTGRESQL_CONFIG_FILE=$HOME/openshift-custom-postgresql.conf

psql_identifier_regex='^[a-zA-Z_][a-zA-Z0-9_]*$'
psql_password_regex='^[a-zA-Z0-9_~!@#$%^&*()-=<>,.?;:|]+$'

function usage() {
  if [ $# == 2 ]; then
    echo "error: $1"
  fi
  echo "You must specify following environment variables:"
  echo "  POSTGRESQL_USER (regex: '$psql_identifier_regex')"
  echo "  POSTGRESQL_PASSWORD (regex: '$psql_password_regex')"
  echo "  POSTGRESQL_DATABASE (regex: '$psql_identifier_regex')"
  echo "Optional:"
  echo "  POSTGRESQL_ADMIN_PASSWORD (regex: '$psql_password_regex')"
  echo "  POSTGRESQL_REPLICA (true or false)"
  echo "  POSTGRESQL_MASTER (host or ip address of master)"
  echo "Settings:"
  echo "  POSTGRESQL_MAX_CONNECTIONS (default: 100)"
  echo "  POSTGRESQL_SHARED_BUFFERS (default: 32MB)"
  exit 1
}

function check_env_vars() {
  if ! [[ -v POSTGRESQL_USER && -v POSTGRESQL_PASSWORD && -v POSTGRESQL_DATABASE ]]; then
    usage
  fi

  [[ "$POSTGRESQL_USER"     =~ $psql_identifier_regex ]] || usage
  [ ${#POSTGRESQL_USER} -le 63 ] || usage "PostgreSQL username too long (maximum 63 characters)"
  [[ "$POSTGRESQL_PASSWORD" =~ $psql_password_regex   ]] || usage
  [[ "$POSTGRESQL_DATABASE" =~ $psql_identifier_regex ]] || usage
  [ ${#POSTGRESQL_DATABASE} -le 63 ] || usage "Database name too long (maximum 63 characters)"
  if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
    [[ "$POSTGRESQL_ADMIN_PASSWORD" =~ $psql_password_regex ]] || usage
  fi
}

# Make sure env variables don't propagate to PostgreSQL process.
function unset_env_vars() {
  unset POSTGRESQL_USER
  unset POSTGRESQL_PASSWORD
  unset POSTGRESQL_DATABASE
  unset POSTGRESQL_ADMIN_PASSWORD
  unset POSTGRESQL_REPLICA
  unset POSTGRESQL_MASTER
}

function wait_for_postgresql_master() {
  local master_addr=""
  while [ true ]; do
    master_addr=$(postgresql_master_addr)
    [ ! -z "${master_addr}" ] && break
    echo "Waiting for PostgreSQL master service ..."
    sleep 1
  done
  echo "Got PostgreSQL master service address: ${master_addr}"
  while [ true ]; do
    # TODO port to PostgreSQL
    # mysqladmin --host=${master_addr} --user="${MYSQL_MASTER_USER}" \
    #   --password="${_MASTER_PASSWORD}" ping &>/dev/null && return 0
    echo "Waiting for PostgreSQL master (${master_addr}) to accept connections ..."
    sleep 1
  done
}

# postgresql_master_addr lookups the 'postgresql-master' DNS and get list of the available
# endpoints. Each endpoint is a PostgreSQL container with the 'master' PostgreSQL running.
function postgresql_master_addr() {
  local service_name=${POSTGRESQL_MASTER_SERVICE_NAME:-postgresql-master}
  local endpoints=$(dig ${service_name} A +search +short 2>/dev/null)
  # FIXME: This is for debugging (docker run)
  if [ -v POSTGRESQL_MASTER_IP ]; then
    endpoints=${POSTGRESQL_MASTER_IP-}
  fi
  echo -n "$(echo $endpoints | cut -d ' ' -f 1)"
}

# New config is generated every time a container is created. It only contains
# additional custom settings and is included from $PGDATA/postgresql.conf.
function generate_postgresql_config() 
  envsubst < ${POSTGRESQL_CONFIG_FILE}.template > ${POSTGRESQL_CONFIG_FILE}
}

# Generate passwd file based on current uid
function generate_passwd_file() {
  export USER_ID=$(id -u)
  envsubst < ${HOME}/passwd.template > ${HOME}/passwd
  export LD_PRELOAD=libnss_wrapper.so
  export NSS_WRAPPER_PASSWD=/var/lib/pgsql/passwd
  export NSS_WRAPPER_GROUP=/etc/group
}

function initialize_database() {
  check_env_vars

  # Initialize the database cluster with utf8 support enabled by default.
  # This might affect performance, see:
  # http://www.postgresql.org/docs/9.2/static/locale.html
  LANG=${LANG:-en_US.utf8} initdb

  # PostgreSQL configuration.
  cat >> "$PGDATA/postgresql.conf" <<EOF

# Custom OpenShift configuration:
include '${POSTGRESQL_CONFIG_FILE}'
EOF

  # Access control configuration.
  cat >> "$PGDATA/pg_hba.conf" <<EOF

#
# Custom OpenShift configuration starting at this point.
#

# Allow connections from all hosts.
host all all all md5
# Allow replication connections from all hosts.
host replication all all md5
EOF

  pg_ctl -w start
  createuser "$POSTGRESQL_USER"
  createdb --owner="$POSTGRESQL_USER" "$POSTGRESQL_DATABASE"
  psql --command "ALTER USER \"${POSTGRESQL_USER}\" WITH ENCRYPTED PASSWORD '${POSTGRESQL_PASSWORD}';"
  psql --command "ALTER USER \"${POSTGRESQL_USER}\" WITH REPLICATION ;"

  if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
    psql --command "ALTER USER \"postgres\" WITH ENCRYPTED PASSWORD '${POSTGRESQL_ADMIN_PASSWORD}';"
  fi

  pg_ctl stop
}