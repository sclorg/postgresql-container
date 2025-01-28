# PostgreSQL 16 SQL Database Server Container Image

This container image features the PostgreSQL 16 SQL database server, suitable for OpenShift and general applications. Users have the option to select from RHEL, CentOS Stream, and Fedora-based images. RHEL images can be found in the [Red Hat Container Catalog](https://access.redhat.com/containers/), while CentOS Stream images are available on [Quay.io](https://quay.io/organization/sclorg), and Fedora images can be accessed in [Quay.io](https://quay.io/organization/fedora). The resulting image can be executed using [podman](https://github.com/containers/libpod).

Please note that while the examples provided in this README utilize `podman`, it is possible to substitute any instance of `podman` with `docker` and the same arguments. `podman` can be installed with on Fedora with command `dnf install podman-docker`.

## Overview

This container image offers a containerized version of the PostgreSQL postgres daemon and client application. The postgres server daemon accepts client connections and grants access to PostgreSQL database content on behalf of said clients. For more information regarding the PostgreSQL project, please visit the official project website (https://www.postgresql.org/).

## Usage

Assuming you are utilizing the `` image, which is accessible via the `postgresql:16` imagestream tag in Openshift, the following steps outline usage. To set only the mandatory environment variables without storing the database in a host directory, execute this command:

```bash
$ podman run -d --name postgresql_database -e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=pass -e POSTGRESQL_DATABASE=db -p 5432:5432 
```

This command creates a container named `postgresql_database` running PostgreSQL with the database `db` and a user with the credentials `user:pass`.

> Note: The user `postgres` is reserved for internal usage

Port 5432 will be exposed and mapped to the host. For persistent database storage across container executions, include the `-v /host/db/path:/var/lib/pgsql/data` argument (refer to the information below). This directory will serve as the PostgreSQL database cluster.

In an Openshift environment, the same can be achieved using templates provided by Openshift or found in [examples](https://github.com/sclorg/postgresql-container/tree/master/examples):

```bash
$ oc process -f examples/postgresql-ephemeral-template.json -p POSTGRESQL_VERSION=16 -p POSTGRESQL_USER=user -p POSTGRESQL_PASSWORD=pass -p POSTGRESQL_DATABASE=db | oc create -f -
```

If the database cluster directory has not been initialized, the entrypoint script will first run [`initdb`](http://www.postgresql.org/docs/16/static/app-initdb.html) to set up the necessary database users and passwords. Once the database has been initialized or if it was previously in place,[`postgres`](http://www.postgresql.org/docs/16/static/app-postgres.html) will be executed and run as PID 1. The detached container can be stopped using `podman stop postgresql_database`.

## Environment Variables and Volumes

The image recognizes the following environment variables, which can be set during initialization by passing `-e VAR=VALUE` to the Docker run command.

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

**`POSTGRESQL_SHARED_BUFFERS (default: 1/4 of memory limit or 32M)`**
Sets how much memory is dedicated to PostgreSQL to use for caching data

**`POSTGRESQL_EFFECTIVE_CACHE_SIZE (default: 1/2 of memory limit or 128M)`**
Set to an estimate of how much memory is available for disk caching by the operating system and within the database itself

**`POSTGRESQL_LOG_DESTINATION (default: /var/lib/pgsql/data/userdata/log/postgresql-*.log)`**  
 Where to log errors, the default is `/var/lib/pgsql/data/userdata/log/postgresql-*.log` and this file is rotated; it can be changed to `/dev/stderr` to make debugging easier

The following environment variables deal with extensions. They are all optional, and if not set, no extensions will be enabled.

**`POSTGRESQL_LIBRARIES`**
       A comma-separated list of libraries that Postgres will preload using shared_preload_libraries.

**`POSTGRESQL_EXTENSIONS`**
       A space-separated list of extensions to create when the server start. Once created, the extensions will stay even if the variable is cleared.


You can also set the following mount points by passing the `-v /host/dir:/container/dir:Z` flag to Docker.

**`/var/lib/pgsql/data`**  
 PostgreSQL database cluster directory

**Notice: When mouting a directory from the host into the container, ensure that the mounted
directory has the appropriate permissions and that the owner and group of the directory
matches the user UID or name which is running inside the container.**

Typically (unless you use `podman run -u` option) processes in container
run under UID 26, so -- on GNU/Linux -- you can fix the datadir permissions
for example by:

```bash
$ setfacl -m u:26:-wx /your/data/dir
$ podman run <...> -v /your/data/dir:/var/lib/pgsql/data:Z <...>
```

## Data Migration

The PostgreSQL container supports data migration from a remote PostgreSQL server. Execute the following command to initiate the process:

```bash
$ podman run -d --name postgresql_database \
    -e POSTGRESQL_MIGRATION_REMOTE_HOST=172.17.0.2 \
    -e POSTGRESQL_MIGRATION_ADMIN_PASSWORD=remoteAdminP@ssword \
    [ OPTIONAL_CONFIGURATION_VARIABLES ]
    rhel8/postgresql-13
```

The migration is performed using the **dump and restore** method (running `pg_dumpall` against the remote cluster and importing the dump locally using `psql`). The process is streamed (via a Unix pipeline), eliminating the need for intermediate dump files and conserving storage space.

If some SQL commands fail during the application, the default behavior of the migration script is to fail, ensuring an **all** or **nothing** outcome for scripted, unattended migration. In most cases, successful migration is expected (but not guaranteed) when migrating from a previous version of the PostgreSQL server container created using the same principles as this one (e.g., migration from `rhel8/postgresql-12` to `rhel8/postgresql-13`).
Migration from a different type of PostgreSQL container may likely fail.

If the **all or nothing** principle is unsuitable for your needs and you are aware of the risks, the optional `POSTGRESQL_MIGRATION_IGNORE_ERRORS` option offers a **best effort** migration (some data may be lost; users must review the standard error output and address issues manually after migration).

Please note that the container image provides assistance for user convenience, but fully automatic migration is not guaranteed. Before starting the database migration, be prepared to perform manual steps to ensure all data is migrated.

Do not use variables like `POSTGRESQL_USER`in migration scenarios, as all data (including information about databases, roles, and passwords) is copied from the old cluster. Make sure to use the same `OPTIONAL_CONFIGURATION_VARIABLES`as you did when initializing the old PostgreSQL container. If the remote cluster has some non-default configurations, you may need to manually copy the configuration files.

**Security warning**: Be aware that IP communication between the old and new PostgreSQL clusters is not encrypted by default. Users must configure SSL on the remote cluster or ensure security through other means.

## PostgreSQL Auto-Tuning

When running the PostgreSQL image with the `--memory` parameter set, and no values provided for `POSTGRESQL_SHARED_BUFFERS` and
`POSTGRESQL_EFFECTIVE_CACHE_SIZE` these values are automatically calculated based on the `--memory` parameter value.

The values are determined using the [upstream](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server) formulas. For `shared_buffers` 1/4 of the provided memory is used, and for `effective_cache_size`, 1/2 of the provided memory is set.

## PostgreSQL Admin Account

By default, the admin account `postgres` has no password set, allowing only local connections. To set a password, define the `POSTGRESQL_ADMIN_PASSWORD` environment variable when initializing your container. This allows you to log in to the `postgres` account remotely, while local connections still do not require a password.

## Changing Passwords

As passwords are part of the image configuration, the only supported method for changing passwords for the database user (`POSTGRESQL_USER`) and `postgres`
admin user is by changing the environment variables `POSTGRESQL_PASSWORD` and `POSTGRESQL_ADMIN_PASSWORD`, respectively.

Changing database passwords through SQL statements or any other method than the environment variables mentioned above will cause a mismatch between the stored variable values and the actual passwords. When a database container starts, it will reset the passwords to the values stored in the environment variables.

## Extending Image

You can extend this image in Openshift using the `Source` build strategy or via the standalone [source-to-image](https://github.com/openshift/source-to-image) application (where available). For this example, assume that you are using the `` image, available via `postgresql:16` imagestream tag in Openshift.

To build a customized image `new-postgresql` with configuration from `https://github.com/sclorg/postgresql-container/tree/master/examples/extending-image`, run:

```bash
$ oc new-app postgresql:16~https://github.com/sclorg/postgresql-container.git \
  --name new-postgresql \
  --context-dir examples/extending-image/ \
  -e POSTGRESQL_USER=user \
  -e POSTGRESQL_DATABASE=db \
  -e POSTGRESQL_PASSWORD=password
```

or via `s2i`:

```
$ s2i build --context-dir examples/extending-image/ https://github.com/sclorg/postgresql-container.git  new-postgresql
```

The directory passed to Openshift should contain one or more of the following directories:

##### `postgresql-pre-start/`

This directory should contain `*.sh` files that will be sourced during the early start of the container. At this point, there is no PostgreSQL daemon running in the background.

##### `postgresql-cfg/`

Configuration files (`*.conf`) contained in this directory will be included at the end of the image's postgresql.conf file.

##### `postgresql-init/`

This directory should contain shell scripts (`*.sh`) that are sourced when the database is freshly initialized (after a successful initdb run, which makes the data directory non-empty). At the time of sourcing these scripts, the local PostgreSQL server is running. For re-deployment scenarios with a persistent data directory, the scripts are not sourced (no-op).

##### `postgresql-start/`

This directory has the same semantics as `postgresql-init/`, except that these scripts are always sourced (after `postgresql-init/` scripts, if they exist).

---

During the s2i build, all provided files are copied into the `/opt/app-root/src`
directory in the new image. Only one file with the same name can be used for customization, and user-provided files take precedence over default files in `/usr/share/container-scripts/`. This means that it is possible to overwrite the default files.

## Troubleshooting

Initially, the postgres daemon logs are written to the standard output, making them accessible within the container log. To examine the log, execute the following command:

```bash
podman logs <container>
```

Subsequently, log output is redirected to the logging collector process and will appear in the "pg_log" directory.

## Additional Resources

The Dockerfile and other sources related to this container image can be found at https://github.com/sclorg/postgresql-container. In this repository, the RHEL8 Dockerfile is named Dockerfile.rhel8, the RHEL9 Dockerfile is named Dockerfile.rhel9, the RHEL10 Dockerfile is named Dockerfile.rhel10, and the Fedora Dockerfile is named Dockerfile.fedora.
