FROM centos:centos7
MAINTAINER  Martin Nagy <mnagy@redhat.com>

# PostgreSQL image for OpenShift.
# Volumes:
#  * /var/lib/psql/data   - Database cluster for PostgreSQL
# Environment:
#  * $POSTGRESQL_USER     - Database user name
#  * $POSTGRESQL_PASSWORD - User's password
#  * $POSTGRESQL_DATABASE - Name of the database to create
#  * $POSTGRESQL_ADMIN_PASSWORD (Optional) - Password for the 'postgres'
#                           PostgreSQL administrative account

# Image metadata
ENV POSTGRESQL_VERSION      9.2
ENV IMAGE_DESCRIPTION       PostgreSQL 9.2
ENV IMAGE_TAGS              postgresql,postgresql92
ENV IMAGE_EXPOSE_SERVICES   5432:postgresql

EXPOSE 5432

# This image must forever use UID 26 for postgres user so our volumes are
# safe in the future. This should *never* change, the last test is there
# to make sure of that.
RUN rpmkeys --import file:///etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-7 && \
    yum -y --setopt=tsflags=nodocs install https://www.softwarecollections.org/en/scls/rhscl/postgresql92/epel-7-x86_64/download/rhscl-postgresql92-epel-7-x86_64.noarch.rpm && \
    yum -y --setopt=tsflags=nodocs install postgresql92 && \
    yum clean all && \
    mkdir -p /var/lib/pgsql/data && chown postgres.postgres /var/lib/pgsql/data && \
    test "$(id postgres)" = "uid=26(postgres) gid=26(postgres) groups=26(postgres)"

COPY run-postgresql.sh /usr/local/bin/
COPY contrib/.bashrc /var/lib/pgsql/

VOLUME ["/var/lib/pgsql/data"]

USER postgres

ENTRYPOINT ["run-postgresql.sh"]
CMD ["postgres"]
