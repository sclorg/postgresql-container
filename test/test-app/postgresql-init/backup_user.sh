# Check that user credentials for backup is set

[[ -v POSTGRESQL_BACKUP_USER && -v POSTGRESQL_BACKUP_PASSWORD ]] || usage "You have to set all variables for user for doing backup: POSTGRESQL_BACKUP_USER, POSTGRESQL_BACKUP_PASSWORD"

# create backup user with 'backup' database
psql --variable=user="$POSTGRESQL_BACKUP_USER" \
     --variable=password="$POSTGRESQL_BACKUP_PASSWORD" \
     <<<"
CREATE USER :user SUPERUSER  password :'password';
CREATE DATABASE backup OWNER = :user;
ALTER USER :user set default_transaction_read_only = on;
"
