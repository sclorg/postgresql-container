# Configuration settings.
export POSTGRESQL_MAX_CONNECTIONS=${POSTGRESQL_MAX_CONNECTIONS:-100}
export POSTGRESQL_MAX_PREPARED_TRANSACTIONS=${POSTGRESQL_MAX_PREPARED_TRANSACTIONS:-0}

# Perform auto-tuning based on the container cgroups limits (only when the
# limits are set).
# Users can still override this by setting the POSTGRESQL_SHARED_BUFFERS
# and POSTGRESQL_EFFECTIVE_CACHE_SIZE variables.
if [[ "${NO_MEMORY_LIMIT:-}" == "true" || -z "${MEMORY_LIMIT_IN_BYTES:-}" ]]; then
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

export POSTGRESQL_LOG_DESTINATION=${POSTGRESQL_LOG_DESTINATION:-}

export POSTGRESQL_RECOVERY_FILE=$HOME/openshift-custom-recovery.conf
export POSTGRESQL_CONFIG_FILE=$HOME/openshift-custom-postgresql.conf

postinitdb_actions=

# match . files when moving userdata below
shopt -s dotglob
# extglob enables the !(userdata) glob pattern below.
shopt -s extglob

function usage() {
  if [ $# == 1 ]; then
    echo >&2 "error: $1"
  fi

  cat >&2 <<EOF
For general container run, you must either specify the following environment
variables:
  POSTGRESQL_USER  POSTGRESQL_PASSWORD  POSTGRESQL_DATABASE
Or the following environment variable:
  POSTGRESQL_ADMIN_PASSWORD
Or both.

To migrate data from different PostgreSQL container:
  POSTGRESQL_MIGRATION_REMOTE_HOST (hostname or IP address)
  POSTGRESQL_MIGRATION_ADMIN_PASSWORD (password of remote 'postgres' user)
And optionally:
  POSTGRESQL_MIGRATION_IGNORE_ERRORS=yes (default is 'no')

Optional settings:
  POSTGRESQL_MAX_CONNECTIONS (default: 100)
  POSTGRESQL_MAX_PREPARED_TRANSACTIONS (default: 0)
  POSTGRESQL_SHARED_BUFFERS (default: 32MB)

For more information see /usr/share/container-scripts/postgresql/README.md
within the container or visit https://github.com/sclorg/postgresql-container.
EOF
  exit 1
}

function check_env_vars() {
  if [[ -v POSTGRESQL_USER || -v POSTGRESQL_PASSWORD || -v POSTGRESQL_DATABASE ]]; then
    # one var means all three must be specified
    [[ -v POSTGRESQL_USER && -v POSTGRESQL_PASSWORD && -v POSTGRESQL_DATABASE ]] || usage

    [ ${#POSTGRESQL_USER}     -le 63 ] || usage "PostgreSQL username too long (maximum 63 characters)"
    [ ${#POSTGRESQL_DATABASE} -le 63 ] || usage "Database name too long (maximum 63 characters)"
    postinitdb_actions+=",simple_db"
  fi

  if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
    postinitdb_actions+=",admin_pass"
  fi

  if [ -v POSTGRESQL_MIGRATION_REMOTE_HOST -a \
       -v POSTGRESQL_MIGRATION_ADMIN_PASSWORD ]; then
    postinitdb_actions+=",migration"
  fi

  case "$postinitdb_actions" in
    ,simple_db,admin_pass) ;;
    ,migration|,simple_db|,admin_pass) ;;
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

# Converts the version in format x.y or x.y.z to a number.
version2number ()
{
    local old_IFS=$IFS
    local to_print= depth=${2-3} width=${3-2} sum=0 one_part
    IFS='.'
    set -- $1
    while test $depth -ge 1; do
        depth=$(( depth - 1 ))
        part=${1-0} ; shift || :
        printf "%0${width}d" "$part"
    done
    IFS=$old_IFS
}

# On non-intel arches, data_sync_retry = off does not work
# Upstream discussion: https://www.postgresql.org/message-id/CA+mCpegfOUph2U4ZADtQT16dfbkjjYNJL1bSTWErsazaFjQW9A@mail.gmail.com
# Upstream changes that caused this issue:
# https://github.com/postgres/postgres/commit/483520eca426fb1b428e8416d1d014ac5ad80ef4
# https://github.com/postgres/postgres/commit/9ccdd7f66e3324d2b6d3dec282cfa9ff084083f1
# RHBZ: https://bugzilla.redhat.com/show_bug.cgi?id=1779150
# Special handle of data_sync_retry should handle only in some cases.
# These cases are: non-intel architectures, and version higher or equal 12.0, 10.7, 9.6.12
# Return value 0 means the hack is needed.
function should_hack_data_sync_retry() {
  [ "$(uname -m)" == 'x86_64' ] && return 1
  local version_number=$(version2number "$(pg_ctl -V | sed -e 's/^pg_ctl (PostgreSQL) //')")
  # this matches all 12.x and versions of 10.x where we need the hack
  [ "$version_number" -ge 100700 ] && return 0
  # this matches all 10.x that were not matched above
  [ "$version_number" -ge 100000 ] && return 1
  # this matches all 9.x where need the hack
  [ "$version_number" -ge 090612 ] && return 0
  # all rest should be older 9.x releases
  return 1
}

function generate_postgresql_libraries_config() {
  if [ -v POSTGRESQL_LIBRARIES ]; then
    echo "shared_preload_libraries='${POSTGRESQL_LIBRARIES}'" >> "${POSTGRESQL_CONFIG_FILE}"
  fi
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

  if should_hack_data_sync_retry ; then
    echo "data_sync_retry = on" >>"${POSTGRESQL_CONFIG_FILE}"
  fi

  # For easier debugging, allow users to log to stderr (will be visible
  # in the pod logs) using a single variable
  # https://github.com/sclorg/postgresql-container/issues/353
  if [ -n "${POSTGRESQL_LOG_DESTINATION:-}" ] ; then
    echo "log_destination = 'stderr'" >>"${POSTGRESQL_CONFIG_FILE}"
    echo "logging_collector = on" >>"${POSTGRESQL_CONFIG_FILE}"
    echo "log_directory = '$(dirname "${POSTGRESQL_LOG_DESTINATION}")'" >>"${POSTGRESQL_CONFIG_FILE}"
    echo "log_filename = '$(basename "${POSTGRESQL_LOG_DESTINATION}")'" >>"${POSTGRESQL_CONFIG_FILE}"
  fi

  generate_postgresql_libraries_config
  (
  shopt -s nullglob
  for conf in "${APP_DATA}"/src/postgresql-cfg/*.conf; do
    echo include \'${conf}\' >> "${POSTGRESQL_CONFIG_FILE}"
  done
  )
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
  grep -v -e ^postgres -e ^$USER_ID -e ^$(id -un) /etc/passwd > "$HOME/passwd"
  echo "postgres:x:${USER_ID}:${GROUP_ID}:PostgreSQL Server:${HOME}:/bin/bash" >> "$HOME/passwd"
  export LD_PRELOAD=libnss_wrapper.so
  export NSS_WRAPPER_PASSWD=${HOME}/passwd
  export NSS_WRAPPER_GROUP=/etc/group
}

initdb_wrapper ()
{
  # Initialize the database cluster with utf8 support enabled by default.
  # This might affect performance, see:
  # http://www.postgresql.org/docs/16/static/locale.html
  LANG=${LANG:-en_US.utf8} "$@"
}

function initialize_database() {
  initdb_wrapper initdb

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
    echo "ALTER DATABASE postgres OWNER TO $POSTGRESQL_MASTER_USER;" | psql
    echo "GRANT ALL PRIVILEGES on DATABASE postgres TO $POSTGRESQL_MASTER_USER;" | psql
  fi
}

migrate_db ()
{
    test "$postinitdb_actions" = ",migration" || return 0

    set -o pipefail
    # Migration path.
    (
        if [ ${POSTGRESQL_MIGRATION_IGNORE_ERRORS-no} = no ]; then
            echo '\set ON_ERROR_STOP on'
        fi
        # initdb automatically creates 'postgres' role;  creating it again would
        # fail the whole migration so we drop it here
        PGPASSWORD="$POSTGRESQL_MIGRATION_ADMIN_PASSWORD" \
        pg_dumpall -h "$POSTGRESQL_MIGRATION_REMOTE_HOST" \
            | grep -v '^CREATE ROLE postgres;'
    ) | psql
    set +o pipefail
}

function set_pgdata ()
{
  export PGDATA=$HOME/data/userdata
  # create a subdirectory that the user owns
  mkdir -p "$PGDATA"
  # backwards compatibility case, we used to put the data here,
  # move it into our new expected location (userdata)
  if [ -e ${HOME}/data/PG_VERSION ]; then
    pushd "${HOME}/data"
    # move everything except the userdata directory itself, into the userdata directory.
    mv !(userdata) "userdata"
    popd
  fi
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


run_pgupgrade ()
(
  # Remove .pid file if the file persists after ugly shut down
  if [ -f "$PGDATA/postmaster.pid" ] && ! pg_isready > /dev/null; then
    rm -rf "$PGDATA/postmaster.pid"
  fi

  optimized=false
  old_raw_version=${POSTGRESQL_PREV_VERSION//\./}
  new_raw_version=${POSTGRESQL_VERSION//\./}

  old_pgengine=/usr/lib64/pgsql/postgresql-$old_raw_version/bin
  new_pgengine=/usr/bin

  PGDATA_new="${PGDATA}-new"

  printf >&2 "\n==========  \$PGDATA upgrade: %s -> %s  ==========\n\n" \
             "$POSTGRESQL_PREV_VERSION" \
             "$POSTGRESQL_VERSION"

  info_msg () { printf >&2 "\n===>  $*\n\n" ;}

  # pg_upgrade writes logs to cwd, so go to the persistent storage first
  cd "$HOME"/data

  # disable this because of scl_source, 'set +u' just makes the code ugly
  # anyways
  set +u

  case $POSTGRESQL_UPGRADE in
    copy) # we accept this
      ;;
    hardlink)
      optimized=:
      ;;
    *)
      echo >&2 "Unsupported value: \$POSTGRESQL_UPGRADE=$POSTGRESQL_UPGRADE"
      false
      ;;
  esac

  # boot up data directory with old postgres once again to make sure
  # it was shut down properly, otherwise the upgrade process fails
  info_msg "Starting old postgresql once again for a clean shutdown..."
  "${old_pgengine}/pg_ctl" start -w --timeout 86400 -o "-h 127.0.0.1''"
  info_msg "Waiting for postgresql to be ready for shutdown again..."
  "${old_pgengine}/pg_isready" -h 127.0.0.1
  info_msg "Shutting down old postgresql cleanly..."
  "${old_pgengine}/pg_ctl" stop

  # Ensure $PGDATA_new doesn't exist yet, so we can immediately remove it if
  # there's some problem.
  test ! -e "$PGDATA_new"

  # initialize the database
  info_msg "Initialize new data directory; we will migrate to that."
  initdb_cmd=( initdb_wrapper "$new_pgengine"/initdb "$PGDATA_new" )
  eval "\${initdb_cmd[@]} ${POSTGRESQL_UPGRADE_INITDB_OPTIONS-}" || \
    { rm -rf "$PGDATA_new" ; false ; }

  upgrade_cmd=(
      "$new_pgengine"/pg_upgrade
      "--old-bindir=$old_pgengine"
      "--new-bindir=$new_pgengine"
      "--old-datadir=$PGDATA"
      "--new-datadir=$PGDATA_new"
  )

  # Dangerous --link option, we loose $DATADIR if something goes wrong.
  ! $optimized || upgrade_cmd+=(--link)

  # User-specififed options for pg_upgrade.
  eval "upgrade_cmd+=(${POSTGRESQL_UPGRADE_PGUPGRADE_OPTIONS-})"

  # On non-intel arches the data_sync_retry set to on
  sed -i -e 's/data_sync_retry/#data_sync_retry/' "${POSTGRESQL_CONFIG_FILE}"

  # the upgrade
  info_msg "Starting the pg_upgrade process."

  # Once we stop support for PostgreSQL 9.4, we don't need
  # REDHAT_PGUPGRADE_FROM_RHEL hack as we don't upgrade from 9.2 -- that means
  # that we don't need to fiddle with unix_socket_director{y,ies} option.
  REDHAT_PGUPGRADE_FROM_RHEL=1 \
  "${upgrade_cmd[@]}" || { cat $(find "$PGDATA_new"/.. -name pg_upgrade_server.log) ; rm -rf "$PGDATA_new" && false ; }

  # Move the important configuration and remove old data.  This is highly
  # careless, but we can't do more for this over-automatized process.
  info_msg "Swap the old and new PGDATA and cleanup."
  mv "$PGDATA"/*.conf "$PGDATA_new"
  rm -rf "$PGDATA"
  mv "$PGDATA_new" "$PGDATA"

  # Get back the option we changed above
  sed -i -e 's/#data_sync_retry/data_sync_retry/' "${POSTGRESQL_CONFIG_FILE}"

  info_msg "Upgrade DONE."
)


# Run right after container startup, when the data volume is already initialized
# (not initialized by this container run) and thus there exists a chance that
# the data was generated by incompatible PostgreSQL major version.
try_pgupgrade ()
{
  local versionfile="$PGDATA"/PG_VERSION version upgrade_available

  # This file always exists.
  test -f "$versionfile"
  version=$(cat "$versionfile")

  # If we don't support pg_upgrade, skip.
  test -z "${POSTGRESQL_PREV_VERSION-}" && return 0

  if test "$POSTGRESQL_VERSION" = "$version"; then
      # No need to call pg_upgrade.

      # Mistakenly requests upgrade?  If not, just start the DB.
      test -z "${POSTGRESQL_UPGRADE-}" && return 0

      # Make _sure_ we have this safety-belt here, otherwise our users would
      # just specify '-e POSTGRESQL_UPGRADE=hardlink' permanently, even for
      # re-deployment cases when upgrade is not needed.  Setting such
      # unfortunate default could mean that pg_upgrade might (after some user
      # mistake) migrate (or even destruct, especially with --link) the old data
      # directory with limited rollback options, if any.
      echo >&2
      echo >&2 "== WARNING!! =="
      echo >&2 "PostgreSQL server version matches the datadir PG_VERSION."
      echo >&2 "The \$POSTGRESQL_UPGRADE makes no sense and you probably"
      echo >&2 "made some mistake, keeping the variable set you might"
      echo >&2 "risk a data loss in future!"
      echo >&2 "==============="
      echo >&2

      # Exit here, but allow _really explicit_ foot-shot.
      ${POSTGRESQL_UPGRADE_FORCE-false}
      return 0
  fi

  # At this point in code we know that PG_VERSION doesn't match the PostgreSQL
  # server major version;  this might mean that user either (a) mistakenly
  # deploys from a bad image, or (b) user wants to perform upgrade.  For the
  # upgrade we require explicit request -- just to avoid disasters in (a)-cases.

  if test -z "${POSTGRESQL_UPGRADE-}"; then
    echo >&2 "Incompatible data directory.  This container image provides"
    echo >&2 "PostgreSQL '$POSTGRESQL_VERSION', but data directory is of"
    echo >&2 "version '$version'."
    echo >&2
    echo >&2 "This image supports automatic data directory upgrade from"
    echo >&2 "'$POSTGRESQL_PREV_VERSION', please _carefully_ consult image documentation"
    echo >&2 "about how to use the '\$POSTGRESQL_UPGRADE' startup option."
    # We could wait for postgresql startup failure (there's no risk of data dir
    # corruption), but fail rather early.
    false
  fi

  # We support pg_upgrade process only from previous version of this container
  # (upgrade to N to N+1 is possible, so e.g. 9.4 to 9.5).
  if test "$POSTGRESQL_PREV_VERSION" != "$version"; then
    echo >&2 "With this container image you can only upgrade from data directory"
    echo >&2 "of version '$POSTGRESQL_PREV_VERSION', not '$version'."
    false
  fi

  run_pgupgrade
}

# get_matched_files PATTERN DIR [DIR ...]
# ---------------------------------------
# Print all basenames for files matching PATTERN in DIRs.
get_matched_files ()
{
  local pattern=$1 dir
  shift
  for dir; do
    test -d "$dir" || continue
    find -L "$dir" -maxdepth 1 -type f -name "$pattern" -printf "%f\n"
  done
}

# process_extending_files DIR [DIR ...]
# -------------------------------------
# Source all *.sh files in DIRs in alphabetical order, but if the file exists in
# more then one DIR, source only the first occurrence (first found wins).
process_extending_files()
{
  local filename dir
  while read filename ; do
    for dir in "$@"; do
      local file="$dir/$filename"
      if test -f "$file"; then
        echo "=> sourcing $file ..."
        source "$file"
        set -e # ensure that users don't mistakenly change this
        break
      fi
    done
  done <<<"$(get_matched_files '*.sh' "$@" | sort -u)"
}

create_extensions()
{
  if [ -v POSTGRESQL_EXTENSIONS ]; then
    for EXT in $POSTGRESQL_EXTENSIONS; do
      psql -c "CREATE EXTENSION IF NOT EXISTS ${EXT};"
    done
  fi
}
