#!/bin/bash

_psql () { psql --set ON_ERROR_STOP=1 "$@" ; }

if [[ ",$postinitdb_actions," = *,simple_db,* ]]; then
_psql --set=username="$POSTGRESQL_USER" \
      --set=password="$POSTGRESQL_PASSWORD" \
<<< "ALTER USER :\"username\" WITH ENCRYPTED PASSWORD :'password';"
fi

if [ -v POSTGRESQL_MASTER_USER ]; then
_psql --set=masteruser="$POSTGRESQL_MASTER_USER" \
      --set=masterpass="$POSTGRESQL_MASTER_PASSWORD" \
<<'EOF'
ALTER USER :"masteruser" WITH REPLICATION;
ALTER USER :"masteruser" WITH ENCRYPTED PASSWORD :'masterpass';
EOF
fi

if [ -v POSTGRESQL_ADMIN_PASSWORD ]; then
_psql --set=adminpass="$POSTGRESQL_ADMIN_PASSWORD" \
<<<"ALTER USER \"postgres\" WITH ENCRYPTED PASSWORD :'adminpass';"
fi
