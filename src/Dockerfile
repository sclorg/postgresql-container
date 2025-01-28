FROM {{ spec.s2i_base }}

# PostgreSQL image for OpenShift.
# Volumes:
#  * /var/lib/pgsql/data   - Database cluster for PostgreSQL
# Environment:
#  * $POSTGRESQL_USER     - Database user name
#  * $POSTGRESQL_PASSWORD - User's password
#  * $POSTGRESQL_DATABASE - Name of the database to create
#  * $POSTGRESQL_ADMIN_PASSWORD (Optional) - Password for the 'postgres'
#                           PostgreSQL administrative account

ENV POSTGRESQL_VERSION={{ spec.version }} \
    {% if spec.prod != "rhel8" or spec.prod != "rhel9" or spec.version == "10" %}
    POSTGRESQL_PREV_VERSION={{ spec.prev_version }} \
    {% endif %}
    HOME=/var/lib/pgsql \
    PGUSER=postgres \
    APP_DATA=/opt/app-root

ENV SUMMARY="PostgreSQL is an advanced Object-Relational database management system" \
    DESCRIPTION="PostgreSQL is an advanced Object-Relational database management system (DBMS). \
The image contains the client and server programs that you'll need to \
create, run, maintain and access a PostgreSQL DBMS server."

LABEL summary="$SUMMARY" \
      description="$DESCRIPTION" \
      io.k8s.description="$DESCRIPTION" \
      io.k8s.display-name="PostgreSQL {{ spec.version }}" \
      io.openshift.expose-services="5432:postgresql" \
      io.openshift.tags="{{ spec.openshift_tags }}" \
      io.openshift.s2i.assemble-user="26" \
      name="{{ spec.img_name }}" \
      com.redhat.component="{{ spec.redhat_component }}" \
{% if spec.version not in ["9.4", "9.5", "9.6"] %}
      version="1" \
{% elif spec.version == "9.6" and config.os.id == "rhel" %}
      version="1" \
{% else %}
      version="{{ spec.version }}" \
{% endif %}
{% if config.os.id == 'rhel' %}
      com.redhat.license_terms="https://www.redhat.com/en/about/red-hat-end-user-license-agreements#rhel" \
{% endif %}
      usage="podman run -d --name postgresql_database -e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=pass -e POSTGRESQL_DATABASE=db -p 5432:5432 {{ spec.img_name }}" \
      maintainer="SoftwareCollections.org <sclorg@redhat.com>"

EXPOSE 5432

COPY root/usr/libexec/fix-permissions /usr/libexec/fix-permissions

# This image must forever use UID 26 for postgres user so our volumes are
# safe in the future. This should *never* change, the last test is there
# to make sure of that.
{% if spec.repo_enable_reason %}
{{ spec.repo_enable_reason }}
{% endif %}
{% if spec.prod == "c10s" or spec.prod == "rhel10" %}
RUN INSTALL_PKGS="rsync tar gettext-envsubst bind-utils nss_wrapper-libs glibc-locale-source xz" && \
    PSQL_PKGS="{{ spec.pkgs }}" && \
{% elif spec.prod == "rhel9" and spec.version == "13" %} \
RUN INSTALL_PKGS="rsync tar gettext bind-utils nss_wrapper-libs {{ spec.pkgs }}" && \
{% else %}
RUN {{ spec.environment_setup }}
    INSTALL_PKGS="rsync tar gettext bind-utils nss_wrapper-libs {{ spec.pkgs }}" && \
{% endif %}
{% if spec.version not in ["9.6", "10", "11"] %}
    INSTALL_PKGS="$INSTALL_PKGS pgaudit" && \
    {% if spec.prod != "c10s" %}
    INSTALL_PKGS="$INSTALL_PKGS procps-ng util-linux postgresql-upgrade" && \
    {% endif %}
{% endif %}
{% if spec.prod == "c10s" or spec.prod == "rhel10" %}
    yum -y --setopt=tsflags=nodocs install $INSTALL_PKGS $PSQL_PKGS  && \
    rpm -V $INSTALL_PKGS {{ spec.check_pkgs }} && \
{% else %}
    yum -y --setopt=tsflags=nodocs install $INSTALL_PKGS && \
    rpm -V $INSTALL_PKGS && \
{% endif %}
    postgres -V | grep -qe "$POSTGRESQL_VERSION\." && echo "Found VERSION $POSTGRESQL_VERSION" && \
    {% if spec.post_install %}
    {{ spec.post_install }}
    {% endif %}
    yum -y clean all --enablerepo='*' && \
    localedef -f UTF-8 -i en_US en_US.UTF-8 && \
    test "$(id postgres)" = "uid=26(postgres) gid=26(postgres) groups=26(postgres)" && \
    mkdir -p /var/lib/pgsql/data && \
    mkdir -p /run/postgresql && \
    /usr/libexec/fix-permissions /var/lib/pgsql /run/postgresql

# Get prefix path and path to scripts rather than hard-code them in scripts
ENV CONTAINER_SCRIPTS_PATH=/usr/share/container-scripts/postgresql \
    ENABLED_COLLECTIONS={{ spec.enabled_collection }}

COPY root /
COPY ./s2i/bin/ $STI_SCRIPTS_PATH

# Hard links are not supported in Testing Farm approach during sync to guest
# operation system. Therefore tests are failing on error
# /usr/libexec/s2i/run no such file or directory
RUN ln -s /usr/bin/run-postgresql $STI_SCRIPTS_PATH/run

# Not using VOLUME statement since it's not working in OpenShift Online:
# https://github.com/sclorg/httpd-container/issues/30
# VOLUME ["/var/lib/pgsql/data"]

# S2I permission fixes
# --------------------
# 1. unless specified otherwise (or - equivalently - we are in OpenShift), s2i
#    build process would be executed as 'uid=26(postgres) gid=26(postgres)'.
#    Such process wouldn't be able to execute the default 'assemble' script
#    correctly (it transitively executes 'fix-permissions' script).  So let's
#    add the 'postgres' user into 'root' group here
#
# 2. we call fix-permissions on $APP_DATA here directly (UID=0 during build
#    anyways) to assure that s2i process is actually able to _read_ the
#    user-specified scripting.
RUN usermod -a -G root postgres && \
    /usr/libexec/fix-permissions --read-only "$APP_DATA"

USER 26

ENTRYPOINT ["container-entrypoint"]
CMD ["run-postgresql"]
