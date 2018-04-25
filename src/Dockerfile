FROM {{ spec.s2i_base }}

# PostgreSQL image for OpenShift.
# Volumes:
#  * /var/lib/psql/data   - Database cluster for PostgreSQL
# Environment:
#  * $POSTGRESQL_USER     - Database user name
#  * $POSTGRESQL_PASSWORD - User's password
#  * $POSTGRESQL_DATABASE - Name of the database to create
#  * $POSTGRESQL_ADMIN_PASSWORD (Optional) - Password for the 'postgres'
#                           PostgreSQL administrative account

ENV POSTGRESQL_VERSION={{ spec.version }} \
    POSTGRESQL_PREV_VERSION={{ spec.prev_version }} \
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
      name="{{ spec.org }}/postgresql-{{ spec.short }}-{{ spec.prod }}" \
      com.redhat.component="{{ spec.redhat_component }}" \
{% if spec.version not in ["9.4", "9.5", "9.6"] %}
      version="1" \
{% elif spec.version == "9.6" and config.os.id == "rhel" %}
      version="1" \
{% else %}
      version="{{ spec.version }}" \
{% endif %}
      usage="docker run -d --name postgresql_database -e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=pass -e POSTGRESQL_DATABASE=db -p 5432:5432 {{ spec.org }}/postgresql-{{ spec.short }}-{{ spec.prod }}" \
      maintainer="SoftwareCollections.org <sclorg@redhat.com>"

EXPOSE 5432

COPY root/usr/libexec/fix-permissions /usr/libexec/fix-permissions

# This image must forever use UID 26 for postgres user so our volumes are
# safe in the future. This should *never* change, the last test is there
# to make sure of that.
{% if spec.repo_enable_reason %}
{{ spec.repo_enable_reason }}
{% endif %}
RUN {{ spec.environment_setup }}
{% if not spec.stable and spec.has_devel_repo %}
  {% if config.os.id == 'centos' and spec.has_devel_repo.centos %}
    yum-config-manager --add-repo https://cbs.centos.org/repos/sclo7-rh-postgresql{{ spec.version }}-rh-candidate/x86_64/os/ && \
    echo gpgcheck=0 >> /etc/yum.repos.d/cbs.centos.org_repos_sclo7-rh-postgresql{{ spec.version }}-rh-candidate_x86_64_os_.repo && \
  {% elif config.os.id == 'rhel' %}
    {% if spec.has_devel_repo.rhel == 'brew' %}
    yum-config-manager --add-repo http://download.devel.redhat.com/brewroot/repos/rhscl-{{ spec.rhscl_version.development }}-rh-postgresql{{ spec.version }}-rhel-7-build/latest/x86_64 && \
    echo gpgcheck=0 >> /etc/yum.repos.d/download.devel.redhat.com_brewroot_repos_rhscl-{{ spec.rhscl_version.development }}-rh-postgresql{{ spec.version }}-rhel-7-build_latest_x86_64.repo && \
    {% elif spec.has_devel_repo.rhel == 'beta' %}
    yum-config-manager --enable rhel-server-rhscl-7-beta-rpms && \
    {% endif %}
  {% endif %}
{% endif %}
    INSTALL_PKGS="rsync tar gettext bind-utils nss_wrapper {{ spec.pkgs }}" && \
    yum -y --setopt=tsflags=nodocs install $INSTALL_PKGS && \
    rpm -V $INSTALL_PKGS && \
    yum clean all && \
    localedef -f UTF-8 -i en_US en_US.UTF-8 && \
    test "$(id postgres)" = "uid=26(postgres) gid=26(postgres) groups=26(postgres)" && \
    mkdir -p /var/lib/pgsql/data && \
    /usr/libexec/fix-permissions /var/lib/pgsql && \
    /usr/libexec/fix-permissions /var/run/postgresql

# Get prefix path and path to scripts rather than hard-code them in scripts
ENV CONTAINER_SCRIPTS_PATH=/usr/share/container-scripts/postgresql \
    ENABLED_COLLECTIONS={{ spec.enabled_collection }}

COPY root /
COPY ./s2i/bin/ $STI_SCRIPTS_PATH

# When bash is started non-interactively, to run a shell script, for example it
# looks for this variable and source the content of this file. This will enable
# the SCL for all scripts without need to do 'scl enable'.
ENV BASH_ENV=${CONTAINER_SCRIPTS_PATH}/scl_enable \
    ENV=${CONTAINER_SCRIPTS_PATH}/scl_enable \
    PROMPT_COMMAND=". ${CONTAINER_SCRIPTS_PATH}/scl_enable"

VOLUME ["/var/lib/pgsql/data"]

# {APP_DATA} needs to be accessed by postgres user while s2i assembling
# postgres user changes permissions of files in APP_DATA during assembling
RUN /usr/libexec/fix-permissions ${APP_DATA} && \
    usermod -a -G root postgres

USER 26

ENTRYPOINT ["container-entrypoint"]
CMD ["run-postgresql"]
