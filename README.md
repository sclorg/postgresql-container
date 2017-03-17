PostgreSQL Docker images
========================

This repository contains Dockerfiles for PostgreSQL images for OpenShift.
Users can choose between RHEL and CentOS based images.

For more information about using these images with OpenShift, please see the
official [OpenShift Documentation](https://docs.openshift.org/latest/using_images/db_images/postgresql.html).

Versions
---------------
PostgreSQL versions currently provided are:
* postgresql-9.4
* postgresql-9.5

RHEL versions currently supported are:
* RHEL7

CentOS versions currently supported are:
* CentOS7


Installation
----------------------
Choose either the CentOS7 or RHEL7 based image:

*  **RHEL7 based image**

    To build a RHEL7 based image, you need to run Docker build on a properly
    subscribed RHEL machine.

    ```
    $ git clone --recursive https://github.com/sclorg/postgresql-container.git
    $ cd postgresql
    $ make build TARGET=rhel7 VERSION=9.5
    ```

*  **CentOS7 based image**

    This image is available on DockerHub. To download it run:

    ```
    $ docker pull centos/postgresql-95-centos7
    ```

    To build a PostgreSQL image from scratch run:

    ```
    $ git clone --recursive https://github.com/sclorg/postgresql-container.git
    $ cd postgresql
    $ make build TARGET=centos7 VERSION=9.5
    ```

**Notice: By omitting the `VERSION` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**


Usage
---------------------------------

For information about usage of Dockerfile for PostgreSQL 9.4,
see [usage documentation](9.4/README.md).

For information about usage of Dockerfile for PostgreSQL 9.5,
see [usage documentation](9.5/README.md).

Usage on Atomic host
---------------------------------
Systems derived from projectatomic.io usually include the `atomic` command that is
used to run containers besides other things.

To install a new service `postgresql1` based on this image on such a system, run:

```
$ atomic install -n postgresql1 --opt2='-e POSTGRESQL_USER=user -e POSTGRESQL_PASSWORD=secretpass -e POSTGRESQL_DATABASE=db1 -p 5432:5432' openshift/postgresql-92-centos7
```

Then to run the service, use the standard `systemctl` call:

```
$ systemctl start postgresql1.service
```

In order to work with that service, you may either connect to exposed port 5432 or run this command to connect locally:
```
$ atomic run -n postgresql1 openshift/postgresql-92-centos7 bash -c 'psql'
```

To stop and uninstall the postgresql1 service, run:

```
$ systemctl stop postgresql1.service
$ atomic uninstall -n postgresql1 openshift/postgresql-92-centos7
```


Test
---------------------------------

This repository also provides a test framework, which checks basic functionality
of the PostgreSQL image.

Users can choose between testing PostgreSQL based on a RHEL or CentOS image.

*  **RHEL based image**

    To test a RHEL7 based PostgreSQL image, you need to run the test on a properly
    subscribed RHEL machine.

    ```
    $ cd postgresql
    $ make test TARGET=rhel7 VERSION=9.5
    ```

*  **CentOS based image**

    ```
    $ cd postgresql
    $ make test TARGET=centos7 VERSION=9.5
    ```
+By using the `TEST_CASE` parameter you can choose a test case subset to be run against the image, eg:

    $ cd postgresql
    $ make test VERSION=9.5 TEST_CASE="run_general_tests run_replication_test"


**Notice: By omitting the `VERSION` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**
