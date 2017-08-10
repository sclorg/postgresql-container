% POSTGRESQL-94(1) Container Image Pages
% SoftwareCollections.org
% July 19, 2017

PostgreSQL 9.4 SQL Database Server Docker image
===============================================

This container image includes PostgreSQL 9.4 SQL database server for OpenShift and general usage.
Users can choose between RHEL and CentOS based images.
The RHEL image is available in the [Red Hat Container Catalog](https://access.redhat.com/containers/#/registry.access.redhat.com/rhscl/postgresql-94-rhel7)
as registry.access.redhat.com/rhscl/postgresql-94-rhel7.
The CentOS image is then available on [Docker Hub](https://hub.docker.com/r/centos/postgresql-94-centos7/)
as centos/postgresql-94-centos7.


Description
-----------

This container image provides a containerized packaging of the PostgreSQL postgres daemon
and client application. The postgres server daemon accepts connections from clients
and provides access to content from PostgreSQL databases on behalf of the clients.
You can find more information on the PostgreSQL project from the project Web site
(https://www.postgresql.org/).


Usage
-----

For this, we will assume that you are using the `rhscl/postgresql-94-rhel7` image.
If you want to set only the mandatory environment variables and not store the database
in a host directory, execute the following command:

```
$ docker run -d --name postgresql_database -e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=pass -e POSTGRESQL_DATABASE=db -p 5432:5432 rhscl/postgresql-94-rhel7
```

This will create a container named `postgresql_database` running PostgreSQL with
database `db` and user with credentials `user:pass`. Port 5432 will be exposed
and mapped to the host. If you want your database to be persistent across container
executions, also add a `-v /host/db/path:/var/lib/pgsql/data` argument. This will be
the PostgreSQL database cluster directory.

If the database cluster directory is not initialized, the entrypoint script will
first run [`initdb`](http://www.postgresql.org/docs/9.4/static/app-initdb.html)
and setup necessary database users and passwords. After the database is initialized,
or if it was already present, [`postgres`](http://www.postgresql.org/docs/9.4/static/app-postgres.html)
is executed and will run as PID 1. You can stop the detached container by running
`docker stop postgresql_database`.



Environment variables and volumes
---------------------------------

The image recognizes the following environment variables that you can set during
initialization by passing `-e VAR=VALUE` to the Docker run command.

|    Variable name             |    Description                                 |
| :--------------------------- | ---------------------------------------------- |
|  `POSTGRESQL_USER`           | User name for PostgreSQL account to be created |
|  `POSTGRESQL_PASSWORD`       | Password for the user account                  |
|  `POSTGRESQL_DATABASE`       | Database name                                  |
|  `POSTGRESQL_ADMIN_PASSWORD` | Password for the `postgres` admin account (optional)     |

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


Troubleshooting
---------------
At first the postgres daemon writes its logs to the standard output, so these are available in the container log. The log can be examined by running:

    docker logs <container>

Then log output is redirected to logging collector process and will appear in directory "pg_log".


See also
--------
Dockerfile and other sources for this container image are available on
https://github.com/sclorg/postgresql-container.
In that repository, Dockerfile for CentOS is called Dockerfile, Dockerfile
for RHEL is called Dockerfile.rhel7.
