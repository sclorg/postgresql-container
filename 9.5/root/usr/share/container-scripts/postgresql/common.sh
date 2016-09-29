# Configuration settings.
export POSTGRESQL_MAX_CONNECTIONS=${POSTGRESQL_MAX_CONNECTIONS:-100}
export POSTGRESQL_MAX_PREPARED_TRANSACTIONS=${POSTGRESQL_MAX_PREPARED_TRANSACTIONS:-0}

# Perform auto-tuning based on the container cgroups limits (only when the
# limits are set).
# Users can still override this by setting the POSTGRESQL_SHARED_BUFFERS
# and POSTGRESQL_EFFECTIVE_CACHE_SIZE variables.
if [[ "${NO_MEMORY_LIMIT:-}" == "true" || -z "${MEMORY_LIMIT_IN_BYTES}" ]]; then
    export POSTGRESQL_SHARED_BUFFERS=${POSTGRESQL_SHARED_BUFFERS:-32MB}
    export POSTGRESQL_EFFECTIVE_CACHE_SIZE=${POSTGRESQL_EFFECTIVE_CACHE_SIZE:-128MB}
else
    # Use 1/4 of given memory for shared buffers
    shared_buffers_computed="$(($MEMORY_LIMIT_IN_BYTES/1024/1024/4))MB"
    # Setting effective_cache_size to 1/2 of total memory would be a normal conservative setting,
    effective_cache="$(($MEMORY_LIMIT_IN_BYTES/1024/1024/2))MB"
    export POSTGRESQL_SHARED_BUFFERS=${POSTGRESQL_SHARED_BUFFERS:-$shared_buffers_computed}
    export POSTGRESQL_EFFECTIVE_CACHE_SIZE=${POSTGRESQL_EFFECTIVE_CACHE_SIZE:-$effective_cache}
fi

export POSTGRESQL_RECOVERY_FILE=$HOME/openshift-custom-recovery.conf
export POSTGRESQL_CONFIG_FILE=$HOME/openshift-custom-postgresql.conf

postinitdb_actions=

psql_identifier_regex='^[a-zA-Z_][a-zA-Z0-9_]*$'
psql_password_regex='^[a-zA-Z0-9_~!@#$%^&*()-=<>,.?;:|]+$'

# match . files when moving userdata below
shopt -s dotglob
# extglob enables the !(userdata) glob pattern below.
shopt -s extglob

function usage() {
  if [ $# == 1 ]; then
    echo >&2 "error: $1"
  fi

  cat >&2 <<EOF
You must either specify the following environment variables:
  POSTGRESQL_USER (regex: '$psql_identifier_regex')
  POSTGRESQL_PASSWORD (regex: '$psql_password_regex')
  POSTGRESQL_DATABASE (regex: '$psql_identifier_regex')
Or the following environment variable:
  POSTGRESQL_ADMIN_PASSWORD (regex: '$psql_password_regex')
Or both (or mount secrets in /run/secrets/pgusers/user or /run/secrets/pgusers/admin).
Optional settings:
  POSTGRESQL_MAX_CONNECTIONS (default: 100)
  POSTGRESQL_MAX_PREPARED_TRANSACTIONS (default: 0)
  POSTGRESQL_SHARED_BUFFERS (default: 32MB)

For more information see /usr/share/container-scripts/postgresql/README.md
within the container or visit https://github.com/openshift/postgresql.
EOF
  exit 1
}

check_cred_secret() {
    local credpath="$1"
    [ -f "$credpath/username" ] && \
    [ -f "$credpath/password" ] && \
    [[ "$(<"$credpath/username")" =~ $psql_identifier_regex ]] && \
    [[ "$(<"$credpath/password")" =~ $psql_password_regex ]] &&
    [ "$(wc -c < "$credpath/username")" -le 63 ]
}

function check_env_vars() {
  if [[ -v POSTGRESQL_USER || -v POSTGRESQL_PASSWORD ]]; then
    # one var means all three must be specified
    [[ -v POSTGRESQL_USER && -v POSTGRESQL_PASSWORD && -v POSTGRESQL_DATABASE ]] || usage
    [[ "$POSTGRESQL_USER"     =~ $psql_identifier_regex ]] || usage
    [[ "$POSTGRESQL_PASSWORD" =~ $psql_password_regex   ]] || usage
    [[ "$POSTGRESQL_DATABASE" =~ $psql_identifier_regex ]] || usage
    [ ${#POSTGRESQL_USER}     -le 63 ] || usage "PostgreSQL username too long (maximum 63 characters)"
    [ ${#POSTGRESQL_DATABASE} -le 63 ] || usage "Database name too long (maximum 63 characters)"
    postinitdb_actions+=",simple_db"
  elif check_cred_secret "/run/secrets/pgusers/user" && [ -v POSTGRESQL_DATABASE ]; then
    # one var means all three must be specified
    [[ "$POSTGRESQL_DATABASE" =~ $psql_identifier_regex ]] || usage
    [ ${#POSTGRESQL_DATABASE} -le 63 ] || usage "Database name too long (maximum 63 characters)"
    POSTGRESQL_USER="$(</run/secrets/pgusers/user/username)"
    POSTGRESQL_PASSWORD="$(</run/secrets/pgusers/user/password)"
    postinitdb_actions+=",simple_db"
  fi

  if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
    [[ "$POSTGRESQL_ADMIN_PASSWORD" =~ $psql_password_regex ]] || usage
    postinitdb_actions+=",admin_pass"
  fi

  if check_cred_secret "/run/secrets/pgusers/admin"; then
    [ "$(<"/run/secrets/pgusers/admin/username")" = "postgres" ] || usage
    POSTGRESQL_ADMIN_PASSWORD="$(<"/run/secrets/pgusers/admin/password")"
    postinitdb_actions+=",admin_pass"
  fi

  if check_cred_secret "/run/secrets/pgusers/master"; then
    POSTGRESQL_MASTER_USER="$(<"/run/secrets/pgusers/master/username")"
    POSTGRESQL_MASTER_PASSWORD="$(<"/run/secrets/pgusers/master/password")"
  fi

  case ",$postinitdb_actions," in
    *,admin_pass,*|*,simple_db,*) ;;
    *) usage ;;
  esac

}

# Make sure env variables don't propagate to PostgreSQL process.
function unset_env_vars() {
  unset POSTGRESQL_{DATABASE,USER,PASSWORD,ADMIN_PASSWORD}
}

# postgresql_master_addr lookups the 'postgresql-master' DNS and get list of the available
# endpoints. Each endpoint is a PostgreSQL container with the 'master' PostgreSQL running.
function postgresql_master_addr() {
  local service_name=${POSTGRESQL_MASTER_SERVICE_NAME:-postgresql-master}
  local endpoints=$(dig ${service_name} A +search | grep ";${service_name}" | cut -d ';' -f 2 2>/dev/null)
  # FIXME: This is for debugging (docker run)
  if [ -v POSTGRESQL_MASTER_IP ]; then
    endpoints=${POSTGRESQL_MASTER_IP:-}
  fi
  if [ -z "$endpoints" ]; then
    >&2 echo "Failed to resolve PostgreSQL master IP address"
    exit 3
  fi
  echo -n "$(echo $endpoints | cut -d ' ' -f 1)"
}

# New config is generated every time a container is created. It only contains
# additional custom settings and is included from $PGDATA/postgresql.conf.
function generate_postgresql_config() {
  envsubst \
      < "${CONTAINER_SCRIPTS_PATH}/openshift-custom-postgresql.conf.template" \
      > "${POSTGRESQL_CONFIG_FILE}"

  if [ "${ENABLE_REPLICATION}" == "true" ]; then
    envsubst \
        < "${CONTAINER_SCRIPTS_PATH}/openshift-custom-postgresql-replication.conf.template" \
        >> "${POSTGRESQL_CONFIG_FILE}"
  fi
}

function generate_postgresql_recovery_config() {
  envsubst \
      < "${CONTAINER_SCRIPTS_PATH}/openshift-custom-recovery.conf.template" \
      > "${POSTGRESQL_RECOVERY_FILE}"
}

# Generate passwd file based on current uid
function generate_passwd_file() {
  export USER_ID=$(id -u)
  export GROUP_ID=$(id -g)
  grep -v ^postgres /etc/passwd > "$HOME/passwd"
  echo "postgres:x:${USER_ID}:${GROUP_ID}:PostgreSQL Server:${HOME}:/bin/bash" >> "$HOME/passwd"
  export LD_PRELOAD=libnss_wrapper.so
  export NSS_WRAPPER_PASSWD=${HOME}/passwd
  export NSS_WRAPPER_GROUP=/etc/group
}

function initialize_database() {
  # Initialize the database cluster with utf8 support enabled by default.
  # This might affect performance, see:
  # http://www.postgresql.org/docs/9.5/static/locale.html
  LANG=${LANG:-en_US.utf8} initdb

  # PostgreSQL configuration.
  cat >> "$PGDATA/postgresql.conf" <<EOF

# Custom OpenShift configuration:
include '${POSTGRESQL_CONFIG_FILE}'
EOF

  # Access control configuration.
  # FIXME: would be nice-to-have if we could allow connections only from
  #        specific hosts / subnet
  cat >> "$PGDATA/pg_hba.conf" <<EOF

#
# Custom OpenShift configuration starting at this point.
#

# Allow connections from all hosts.
host all all all md5

# Allow replication connections from all hosts.
host replication all all md5
EOF
}

function create_users() {
  if [[ ",$postinitdb_actions," = *,simple_db,* ]]; then
    createuser "$POSTGRESQL_USER"
    createdb --owner="$POSTGRESQL_USER" "$POSTGRESQL_DATABASE"
  fi

  if [ -v POSTGRESQL_MASTER_USER ]; then
    createuser "$POSTGRESQL_MASTER_USER"
  fi
}

create_user_if_not_exists() {
    psql --set user="$1" <<EOF
DO
\$body$
BEGIN
    IF NOT EXISTS (
        SELECT * FROM pg_catalog.pg_user
        WHERE usename = :'user' )
    THEN
        CREATE USER :"user" LOGIN;
    END IF;
END
\$body$
EOF
}

function set_password() {
    psql --set user="$1" --set pass="$2" \
        --command "ALTER USER :\"user\" WITH ENCRYPTED PASSWORD :'pass';"
}

function set_passwords() {
  if [[ ",$postinitdb_actions," = *,simple_db,* ]]; then
    set_password "$POSTGRESQL_USER" "$POSTGRESQL_PASSWORD"
  fi

  if [ -v POSTGRESQL_MASTER_USER ]; then
    psql --set user="$POSTGRESQL_MASTER_USER" \
        --command "ALTER USER :\"user\" WITH REPLICATION;"
    set_password "$POSTGRESQL_MASTER_USER" "$POSTGRESQL_MASTER_PASSWORD"
  fi

  if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
    set_password postgres "$POSTGRESQL_ADMIN_PASSWORD"
  fi

  # This does not check for recurring user names nor overlaps with passwords
  # set above
  for cred in /run/secrets/pgusers/*; do
      if check_cred_secret "$cred"; then
          local username; username="$(< "$cred/username" )"
          local password; password="$(< "$cred/password" )"
          create_user_if_not_exists "$username"
          set_password "$username" "$password"
      fi
  done
}

function set_pgdata ()
{
  # backwards compatibility case, we used to put the data here,
  # move it into our new expected location (userdata)
  if [ -e ${HOME}/data/PG_VERSION ]; then
    mkdir -p "${HOME}/data/userdata"
    pushd "${HOME}/data"
    # move everything except the userdata directory itself, into the userdata directory.
    mv !(userdata) "userdata"
    popd
  else 
    # create a subdirectory that the user owns
    mkdir -p "${HOME}/data/userdata"
  fi
  export PGDATA=$HOME/data/userdata
  # ensure sane perms for postgresql startup
  chmod 700 "$PGDATA"
}

function wait_for_postgresql_master() {
  while true; do
    master_fqdn=$(postgresql_master_addr)
    echo "Waiting for PostgreSQL master (${master_fqdn}) to accept connections ..."
    if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
      PGPASSWORD=${POSTGRESQL_ADMIN_PASSWORD} psql "postgresql://postgres@${master_fqdn}" -c "SELECT 1;" && return 0
    else
      PGPASSWORD=${POSTGRESQL_PASSWORD} psql "postgresql://${POSTGRESQL_USER}@${master_fqdn}/${POSTGRESQL_DATABASE}" -c "SELECT 1;" && return 0
    fi
    sleep 1
  done
}
