# Manifest for image directories creation
# every dest path will be prefixed by $DESTDIR/$version

DESTDIR='' # optional, defaults to $PWD

# Files containing distgen directives
DISTGEN_RULES="
    src=src/cccp.yml
    dest=cccp.yml;

    src=src/root/usr/share/container-scripts/postgresql/README.md
    dest=root/usr/share/container-scripts/postgresql/README.md;

    src=src/root/usr/share/container-scripts/postgresql/common.sh
    dest=root/usr/share/container-scripts/postgresql/common.sh
"

# Files containing distgen directives, which are used for each
# (distro, version) combination not excluded in multispec
DISTGEN_MULTI_RULES="
    src=src/Dockerfile
    dest=Dockerfile;

    src=src/Dockerfile
    dest=Dockerfile.rhel7
"

# Symbolic links
SYMLINK_RULES="
    link_target=root/usr/share/container-scripts/postgresql/README.md
    link_name=README.md;

    link_target=../test
    link_name=test;

    link_target=/usr/bin/run-postgresql
    link_name=s2i/bin/run
"

# Files to copy
COPY_RULES="
    src=src/root/usr/libexec/fix-permissions
    dest=root/usr/libexec/fix-permissions
    mode=0755;

    src=src/content_sets.yml
    dest=content_sets.yml;

    src=src/root/usr/share/container-scripts/postgresql/openshift-custom-postgresql-replication.conf.template
    dest=root/usr/share/container-scripts/postgresql/openshift-custom-postgresql-replication.conf.template;

    src=src/root/usr/share/container-scripts/postgresql/openshift-custom-postgresql.conf.template
    dest=root/usr/share/container-scripts/postgresql/openshift-custom-postgresql.conf.template;

    src=src/root/usr/share/container-scripts/postgresql/openshift-custom-recovery.conf.template
    dest=root/usr/share/container-scripts/postgresql/openshift-custom-recovery.conf.template;

    src=src/root/usr/bin/cgroup-limits
    dest=root/usr/bin/cgroup-limits
    mode=0755;

    src=src/root/usr/share/container-scripts/postgresql/scl_enable
    dest=root/usr/share/container-scripts/postgresql/scl_enable;

    src=src/root/usr/bin/run-postgresql
    dest=root/usr/bin/run-postgresql
    mode=0755;

    src=src/root/usr/bin/run-postgresql-master
    dest=root/usr/bin/run-postgresql-master
    mode=0755;

    src=src/root/usr/bin/run-postgresql-slave
    dest=root/usr/bin/run-postgresql-slave
    mode=0755;

    src=src/root/usr/bin/container-entrypoint
    dest=root/usr/bin/container-entrypoint
    mode=0755;

    src=src/root/usr/bin/usage
    dest=root/usr/bin/usage
    mode=0755;

    src=src/root/usr/libexec/check-container
    dest=root/usr/libexec/check-container
    mode=0755;

    src=src/root/usr/share/container-scripts/postgresql/start/set_passwords.sh
    dest=root/usr/share/container-scripts/postgresql/start/set_passwords.sh;

    src=src/s2i/bin/assemble
    dest=s2i/bin/assemble
    mode=0755;

    src=src/s2i/bin/usage
    dest=s2i/bin/usage
    mode=0755;
"
