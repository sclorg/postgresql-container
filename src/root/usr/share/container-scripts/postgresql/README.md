PostgreSQL {{ spec.version }} SQL Database Server container image
===============================================

This container image includes PostgreSQL {{ spec.version }} SQL database server for OpenShift and general usage.
Users can choose between RHEL, CentOS and Fedora based images.
The RHEL images are available in the [Red Hat Container Catalog](https://access.redhat.com/containers/),
the CentOS images are available on [Quay.io](https://quay.io/organization/centos7),
and the Fedora images are available in [Fedora Registry](https://registry.fedoraproject.org/).
The resulting image can be run using [podman](https://github.com/containers/libpod).

Note: while the examples in this README are calling `podman`, you can replace any such calls by `docker` with the same arguments


Description
-----------

This container image provides a containerized packaging of the PostgreSQL postgres daemon
and client application. The postgres server daemon accepts connections from clients
and provides access to content from PostgreSQL databases on behalf of the clients.
You can find more information on the PostgreSQL project from the project Web site
(https://www.postgresql.org/).


Usage
-----

For this, we will assume that you are using the `{{ spec.rhel_image_name }}` image, available via `postgresql:{{ spec.version }}` imagestream tag in Openshift.
If you want to set only the mandatory environment variables and not store the database
in a host directory, execute the following command:

```
$ podman run -d --name postgresql_database -e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=pass -e POSTGRESQL_DATABASE=db -p 5432:5432 {{ spec.rhel_image_name }}
```

This will create a container named `postgresql_database` running PostgreSQL with
database `db` and user with credentials `user:pass`. 
> Note: user `postgres` is reserved for internal usage

Port 5432 will be exposed
and mapped to the host. If you want your database to be persistent across container
executions, also add a `-v /host/db/path:/var/lib/pgsql/data` argument (see
below). This will be the PostgreSQL database cluster directory.

The same can be achieved in an Openshift instance using templates provided by Openshift or available in [examples](https://github.com/sclorg/postgresql-container/tree/master/examples):

```
$ oc process -f examples/postgresql-ephemeral-template.json -p POSTGRESQL_VERSION={{ spec.version }} -p POSTGRESQL_USER=user -p POSTGRESQL_PASSWORD=pass -p POSTGRESQL_DATABASE=db | oc create -f -
```

If the database cluster directory is not initialized, the entrypoint script will
first run [`initdb`](http://www.postgresql.org/docs/{{ spec.version }}/static/app-initdb.html)
and setup necessary database users and passwords. After the database is initialized,
or if it was already present, [`postgres`](http://www.postgresql.org/docs/{{ spec.version }}/static/app-postgres.html)
is executed and will run as PID 1. You can stop the detached container by running
`podman stop postgresql_database`.



Environment variables and volumes
---------------------------------

The image recognizes the following environment variables that you can set during
initialization by passing `-e VAR=VALUE` to the Docker run command.

**`POSTGRESQL_USER`**  
       User name for PostgreSQL account to be created

**`POSTGRESQL_PASSWORD`**  
       Password for the user account

**`POSTGRESQL_DATABASE`**  
       Database name

**`POSTGRESQL_ADMIN_PASSWORD`**  
       Password for the `postgres` admin account (optional)


Alternatively, the following options are related to migration scenario:

**`POSTGRESQL_MIGRATION_REMOTE_HOST`**  
       Hostname/IP to migrate from

**`POSTGRESQL_MIGRATION_ADMIN_PASSWORD`**  
       Password for the remote 'postgres' admin user

**`POSTGRESQL_MIGRATION_IGNORE_ERRORS (optional, default 'no')`**  
       Set to 'yes' to ignore sql import errors


The following environment variables influence the PostgreSQL configuration file. They are all optional.

**`POSTGRESQL_MAX_CONNECTIONS (default: 100)`**  
       The maximum number of client connections allowed

**`POSTGRESQL_MAX_PREPARED_TRANSACTIONS (default: 0)`**  
       Sets the maximum number of transactions that can be in the "prepared" state. If you are using prepared transactions, you will probably want this to be at least as large as max_connections

**`POSTGRESQL_SHARED_BUFFERS (default: 32M)`**  
       Sets how much memory is dedicated to PostgreSQL to use for caching data

**`POSTGRESQL_EFFECTIVE_CACHE_SIZE (default: 128M)`**  
       Set to an estimate of how much memory is available for disk caching by the operating system and within the database itself


You can also set the following mount points by passing the `-v /host/dir:/container/dir:Z` flag to Docker.

**`/var/lib/pgsql/data`**  
       PostgreSQL database cluster directory


**Notice: When mouting a directory from the host into the container, ensure that the mounted
directory has the appropriate permissions and that the owner and group of the directory
matches the user UID or name which is running inside the container.**

Typically (unless you use `podman run -u` option) processes in container
run under UID 26, so -- on GNU/Linux -- you can fix the datadir permissions
for example by:

```
$ setfacl -m u:26:-wx /your/data/dir
$ podman run <...> -v /your/data/dir:/var/lib/pgsql/data:Z <...>
```


Data migration
--------------

PostgreSQL container supports migration of data from remote PostgreSQL server.
You can run it like:

```
$ podman run -d --name postgresql_database \
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
----------------------

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
the PostgreSQL server version {{ spec.prev_version }} (and _only_ this version) - provided by sclorg
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

**`copy`**  
       The data files are copied from old datadir to new datadir.  This option has low risk of data loss in case of some upgrade failure.

**`hardlink`**  
       Data files are hard-linked from old to the new data directory, which brings performance optimization - but the old directory becomes unusable, even in case of failure.


Note that because we copy data directory, you need to make sure that you have
enough space for the copy;  upgrade failure because of not enough space might
lead to data loss.


Extending image
----------------

This image can be extended in Openshift using the `Source` build strategy or via the standalone
[source-to-image](https://github.com/openshift/source-to-image) application (where available).
For this, we will assume that you are using the `{{ spec.rhel_image_name }}` image,
available via `postgresql:{{ spec.version }}` imagestream tag in Openshift.

For example to build customized image `new-postgresql`
with configuration from `https://github.com/sclorg/postgresql-container/tree/master/examples/extending-image` run:

```
$ oc new-app postgresql:{{ spec.version }}~https://github.com/sclorg/postgresql-container.git \
  --name new-postgresql \
  --context-dir examples/extending-image/ \
  -e POSTGRESQL_USER=user \
  -e POSTGRESQL_DATABASE=db \
  -e POSTGRESQL_PASSWORD=password
```

or via `s2i`:

```
$ s2i build --context-dir examples/extending-image/ https://github.com/sclorg/postgresql-container.git {{ spec.rhel_image_name }} new-postgresql
```

The directory passed to Openshift should contain one or more of the
following directories:


##### `postgresql-pre-start/`

Source all `*.sh` files from this directory during early start of the
container.  There's no PostgreSQL daemon running on background.


##### `postgresql-cfg/`

Contained configuration files (`*.conf`) will be included at the end of image
postgresql.conf file.


##### `postgresql-init/`

Contained shell scripts (`*.sh`) are sourced when the database is freshly
initialized (after successful initdb run which made the data directory
non-empty).  At the time of sourcing these scripts, the local PostgreSQL
server is running.  For re-deployments scenarios with persistent data
directory, the scripts are not sourced (no-op).


##### `postgresql-start/`

Same sematics as `postgresql-init/`, except that these scripts are
always sourced (after `postgresql-init/` scripts, if they exist).


----------------------------------------------

During the s2i build all provided files are copied into `/opt/app-root/src`
directory in the new image. Only one
file with the same name can be used for customization and user provided files
are preferred over default files in `/usr/share/container-scripts/`-
so it is possible to overwrite them.


Troubleshooting
---------------
At first the postgres daemon writes its logs to the standard output, so these are available in the container log. The log can be examined by running:

    podman logs <container>

Then log output is redirected to logging collector process and will appear in directory "pg_log".


See also
--------
Dockerfile and other sources for this container image are available on
https://github.com/sclorg/postgresql-container.
In that repository, the Dockerfile for CentOS is called Dockerfile, the Dockerfile
for RHEL7 is called Dockerfile.rhel7, the Dockerfile for RHEL8 is called Dockerfile.rhel8,
and the Dockerfile for Fedora is called Dockerfile.fedora.
