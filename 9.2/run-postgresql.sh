#!/bin/bash

# For SCL enablement
source $HOME/.bashrc

set -eu

# Data dir
export PGDATA=/var/lib/pgsql/data

# Be paranoid and stricter than we should be.
psql_identifier_regex='^[a-zA-Z_][a-zA-Z0-9_]*$'
psql_password_regex='^[a-zA-Z0-9_~!@#$%^&*()-=<>,.?;:|]+$'

function usage() {
	if [ $# == 2 ]; then
		echo "error: $1"
	fi
	echo "You must specify following environment variables:"
	echo "  \$POSTGRESQL_USER (regex: '$psql_identifier_regex')"
	echo "  \$POSTGRESQL_PASSWORD (regex: '$psql_password_regex')"
	echo "  \$POSTGRESQL_DATABASE (regex: '$psql_identifier_regex')"
	echo "Optional:"
	echo "  \$POSTGRESQL_ADMIN_PASSWORD (regex: '$psql_password_regex')"
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
}

if [ "$1" = "postgres" -a ! -f "$PGDATA/postgresql.conf" ]; then

	check_env_vars

	# Initialize the database cluster with utf8 support enabled by default.
	# This might affect performance, see:
	# http://www.postgresql.org/docs/9.2/static/locale.html
	LANG=${LANG:-en_US.utf8} initdb

	# PostgreSQL configuration.
	cat >> "$PGDATA/postgresql.conf" <<-EOF

		#
		# Custom OpenShift configuration starting at this point.
		#

		# Listen on all interfaces.
		listen_addresses = '*'
	EOF

	# Access control configuration.
	cat >> "$PGDATA/pg_hba.conf" <<-EOF

		#
		# Custom OpenShift configuration starting at this point.
		#

		# Allow connections from all hosts.
		host all all all md5
	EOF

	pg_ctl -w start
	createuser "$POSTGRESQL_USER"
	createdb --owner="$POSTGRESQL_USER" "$POSTGRESQL_DATABASE"
	psql --command "ALTER USER \"${POSTGRESQL_USER}\" WITH ENCRYPTED PASSWORD '${POSTGRESQL_PASSWORD}';"

	if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
		psql --command "ALTER USER \"postgres\" WITH ENCRYPTED PASSWORD '${POSTGRESQL_ADMIN_PASSWORD}';"
	fi

	pg_ctl stop
fi

unset_env_vars
exec "$@"
