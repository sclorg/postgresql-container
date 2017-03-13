PostgreSQL Docker image
=======================

This repository contains Dockerfiles for PostgreSQL images for general usage and OpenShift.
Users can choose between RHEL and CentOS based images.


Environment variables and volumes
----------------------------------

The image recognizes the following environment variables that you can set during
initialization by passing `-e VAR=VALUE` to the Docker run command.

|    Variable name             |    Description                                 |
| :--------------------------- | ---------------------------------------------- |
|  `POSTGRESQL_USER`           | User name for PostgreSQL account to be created |
|  `POSTGRESQL_PASSWORD`       | Password for the user account                  |
|  `POSTGRESQL_DATABASE`       | Database name                                  |
|  `POSTGRESQL_ADMIN_PASSWORD` | Password for the `postgres` admin account (optional)     |

Alternatively, the following options are related to migration scenario:

|    Variable name                       |    Description                         |
| :------------------------------------- | -------------------------------------- |
|  `POSTGRESQL_MIGRATION_REMOTE_HOST`    | Hostname/IP to migrate from            |
|  `POSTGRESQL_MIGRATION_ADMIN_PASSWORD` | Password for the remote 'postgres' admin user |
|  `POSTGRESQL_MIGRATION_IGNORE_ERRORS`  | Set to 'yes' to ignore sql import errors (optional, default 'no') |

The following environment variables influence the PostgreSQL configuration file. They are all optional.

|    Variable name              |    Description                                                          |    Default
| :---------------------------- | ----------------------------------------------------------------------- | -------------------------------
|  `POSTGRESQL_MAX_CONNECTIONS` | The maximum number of client connections allowed |  100
|  `POSTGRESQL_MAX_PREPARED_TRANSACTIONS` | Sets the maximum number of transactions that can be in the "prepared" state. If you are using prepared transactions, you will probably want this to be at least as large as max_connections |  0
|  `POSTGRESQL_SHARED_BUFFERS`  | Sets how much memory is dedicated to PostgreSQL to use for caching data |  32M
|  `POSTGRESQL_EFFECTIVE_CACHE_SIZE`  | Set to an estimate of how much memory is available for disk caching by the operating system and within the database itself |  128M

You can also set the following mount points by passing the `-v /host:/container` flag to Docker.

|  Volume mount point      | Description                           |
| :----------------------- | ------------------------------------- |
|  `/var/lib/pgsql/data`   | PostgreSQL database cluster directory |

**Notice: When mouting a directory from the host into the container, ensure that the mounted
directory has the appropriate permissions and that the owner and group of the directory
matches the user UID or name which is running inside the container.**

Usage
----------------------

For this, we will assume that you are using the `openshift/postgresql-92-centos7` image.
If you want to set only the mandatory environment variables and not store the database
in a host directory, execute the following command:

```
$ docker run -d --name postgresql_database -e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=pass -e POSTGRESQL_DATABASE=db -p 5432:5432 openshift/postgresql-92-centos7
```

This will create a container named `postgresql_database` running PostgreSQL with
database `db` and user with credentials `user:pass`. Port 5432 will be exposed
and mapped to the host. If you want your database to be persistent across container
executions, also add a `-v /host/db/path:/var/lib/pgsql/data` argument. This will be
the PostgreSQL database cluster directory.

If the database cluster directory is not initialized, the entrypoint script will
first run [`initdb`](http://www.postgresql.org/docs/9.2/static/app-initdb.html)
and setup necessary database users and passwords. After the database is initialized,
or if it was already present, [`postgres`](http://www.postgresql.org/docs/9.2/static/app-postgres.html)
is executed and will run as PID 1. You can stop the detached container by running
`docker stop postgresql_database`.

Data migration
----------------------

PostgreSQL container supports migration of data from remote PostgreSQL server.
You can run it like:

```
$ docker run -d --name postgresql_database \
    -e POSTGRESQL_MIGRATION_REMOTE_HOST=172.17.0.2 \
    -e POSTGRESQL_MIGRATION_ADMIN_PASSWORD=remoteAdminP@ssword \
    [ OPTIONAL_CONFIGURATION_VARIABLES ]
    openshift/postgresql-92-centos7
```

The migration is done the **dump and restore** way (running `pg_dumpall` against
remote cluster and importing the dump locally by `psql`).  Because the process
is streamed (unix pipeline), there are no intermediate dump files created during
this process to not waste additional storage space.

If some SQL commands fail during applying, the default behavior
of the migration script is to fail as well to ensure the **all** or **nothing**
result of scripted, unattended migration. In most common cases, successful
migration is expected (but not guaranteed!), given you migrate from
a previous version of PostgreSQL server container, that is created using
the same principles as this one (e.g. migration from
`openshift/postgresql-92-centos7` to `centos/postgresql-95-centos7`).
Migration from a different kind of PostgreSQL container can likely fail.

If this **all** or **nothing** principle is inadequate for you, and you know
what you are doing, there's optional `POSTGRESQL_MIGRATION_IGNORE_ERRORS` option
which does **best effort** migration (some data might be lost, it is up to user
to review the standard error output and fix the issues manually in
post-migration time).

Please keep in mind that the container image provides help for users'
convenience, but fully automatic migration is not guaranteed.  Thus, before you
start proceeding with the database migration, get prepared to perform manual
steps in order to get all your data migrated.

Note that you might not use variables like `POSTGRESQL_USER` in migration
scenario, all the data (including info about databases, roles or passwords are
copied from old cluster).  Ensure that you use the same
`OPTIONAL_CONFIGURATION_VARIABLES` as you used for initialization of the old
PostgreSQL container.  If some non-default configuration is done on remote
cluster, you might need to copy the configuration files manually, too.

Security warning:  Note that the IP communication between old and new PostgreSQL
clusters is not encrypted by default, it is up to user to configure SSL on
remote cluster or ensure security via different means.

PostgreSQL auto-tuning
--------------------

When the PostgreSQL image is run with the `--memory` parameter set and if there
are no values provided for `POSTGRESQL_SHARED_BUFFERS` and
`POSTGRESQL_EFFECTIVE_CACHE_SIZE` those values are automatically calculated
based on the value provided in the `--memory` parameter.

The values are calculated based on the
[upstream](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)
formulas. For the `shared_buffers` we use 1/4 of given memory and for the
`effective_cache_size` we set the value to 1/2 of the given memory.

PostgreSQL admin account
------------------------
The admin account `postgres` has no password set by default, only allowing local
connections.  You can set it by setting the `POSTGRESQL_ADMIN_PASSWORD` environment
variable when initializing your container. This will allow you to login to the
`postgres` account remotely. Local connections will still not require a password.


Changing passwords
------------------

Since passwords are part of the image configuration, the only supported method
to change passwords for the database user (`POSTGRESQL_USER`) and `postgres`
admin user is by changing the environment variables `POSTGRESQL_PASSWORD` and
`POSTGRESQL_ADMIN_PASSWORD`, respectively.

Changing database passwords through SQL statements or any way other than through
the environment variables aforementioned will cause a mismatch between the
values stored in the variables and the actual passwords. Whenever a database
container starts it will reset the passwords to the values stored in the
environment variables.


Upgrading database (by switching to newer PostgreSQL image version)
-------------------------------------------------------------------

** Warning! Please, before you decide to do the data directory upgrade, always
ensure that you've carefully backed up all your data and that you are OK with
potential manual rollback! **

This image supports automatic upgrade of data directory created by
the PostgreSQL server version 9.4 (and _only_ this version) - provided by sclorg
image.  The upgrade process is designed so that you should be able to just
switch from *image A* to *image B*, and set the `$POSTGRESQL_UPGRADE` variable
appropriately to explicitly request the database data transformation.

The upgrade process is internally implemented via `pg_upgrade` binary, and for
that purpose the container needs to contain two versions of PostgreSQL server
(have a look at `man pg_upgrade` for more info).

For the `pg_upgrade` process - and the new server version, we need to initialize
a brand new data directory.  That's data directory is created automatically by
container tooling under /var/lib/pgsql/data, which is usually external
bind-mountpoint.  The `pg_upgrade` execution is then similar to dump&restore
approach -- it starts both old and new PostgreSQL servers (within container) and
"dumps" the old datadir while and at the same time it "restores" it into new
datadir.  This operation requires a lot of data files copying, so you can decide
what type of upgrade you'll do by setting `$POSTGRESQL_UPGRADE` appropriately:

|    Variable value  |    Description                                 |
| :----------------- | ---------------------------------------------- |
|  `copy`            | The data files are copied from old datadir to new datadir.  This option has low risk of data loss in case of some upgrade failure. |
|  `hardlink`        | Data files are hard-linked from old to the new data directory, which brings performance optimization - but the old directory becomes unusable, even in case of failure. |

Note that because we copy data directory, you need to make sure that you have
enough space for the copy;  upgrade failure because of not enough space might
lead to data loss.
