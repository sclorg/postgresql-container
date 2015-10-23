FROM rhel7.1

# PostgreSQL image for OpenShift.
# Volumes:
#  * /var/lib/psql/data   - Database cluster for PostgreSQL
# Environment:
#  * $POSTGRESQL_USER     - Database user name
#  * $POSTGRESQL_PASSWORD - User's password
#  * $POSTGRESQL_DATABASE - Name of the database to create
#  * $POSTGRESQL_ADMIN_PASSWORD (Optional) - Password for the 'postgres'
#                           PostgreSQL administrative account

ENV POSTGRESQL_VERSION=9.4 \
    HOME=/var/lib/pgsql \
    PGUSER=postgres

LABEL io.k8s.description="PostgreSQL is an advanced Object-Relational database management system" \
      io.k8s.display-name="PostgreSQL 9.4" \
      io.openshift.expose-services="5432:postgresql" \
      io.openshift.tags="database,postgresql,postgresql94,rh-postgresql94"

# Labels consumed by Red Hat build service
LABEL Name="rhscl/postgresql-94-rhel7" \
      BZComponent="rh-postgresql94-docker" \
      Version="9.4" \
      Release="1" \
      Architecture="x86_64"

EXPOSE 5432

# This image must forever use UID 26 for postgres user so our volumes are
# safe in the future. This should *never* change, the last test is there
# to make sure of that.
RUN yum install -y yum-utils gettext && \
    yum-config-manager --enable rhel-server-rhscl-7-rpms && \
    yum-config-manager --enable rhel-7-server-optional-rpms && \
    yum install -y --setopt=tsflags=nodocs bind-utils rh-postgresql94 && \
    yum install -y --disablerepo="epel" --setopt=tsflags=nodocs nss_wrapper && \
    yum clean all && \
    localedef -f UTF-8 -i en_US en_US.UTF-8 && \
    mkdir -p /var/lib/pgsql/data && chown postgres.postgres /var/lib/pgsql/data && \
    test "$(id postgres)" = "uid=26(postgres) gid=26(postgres) groups=26(postgres)" && \
    # Loosen permission bits to avoid problems running container with arbitrary UID
    chmod -R a+rwx /var/run/postgresql

COPY run-*.sh /usr/local/bin/
COPY contrib /var/lib/pgsql/

# Loosen permission bits to avoid problems running container with arbitrary UID
RUN chmod -R a+rwx /var/lib/pgsql

# When bash is started non-interactively, to run a shell script, for example it
# looks for this variable and source the content of this file. This will enable
# the SCL for all scripts without need to do 'scl enable'.
ENV BASH_ENV=/var/lib/pgsql/scl_enable \
    ENV=/var/lib/pgsql/scl_enable \
    PROMPT_COMMAND=". /var/lib/pgsql/scl_enable"

VOLUME ["/var/lib/pgsql/data"]

USER 26

ENTRYPOINT ["run-postgresql.sh"]
CMD ["postgres"]
