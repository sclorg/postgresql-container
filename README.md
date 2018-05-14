PostgreSQL container images
========================

This repository contains Dockerfiles for PostgreSQL images for OpenShift.
Users can choose between RHEL, Fedora and CentOS based images.

For more information about using these images with OpenShift, please see the
official [OpenShift Documentation](https://docs.openshift.org/latest/using_images/db_images/postgresql.html).

For more information about contributing, see
[the Contribution Guidelines](https://github.com/sclorg/welcome/blob/master/contribution.md).
For more information about concepts used in these container images, see the
[Landing page](https://github.com/sclorg/welcome).


Versions
---------------
PostgreSQL versions currently provided are:
* [postgresql-9.5](https://github.com/sclorg/postgresql-container/tree/generated/9.5)
* [postgresql-9.6](https://github.com/sclorg/postgresql-container/tree/generated/9.6)
* [postgresql-10](https://github.com/sclorg/postgresql-container/tree/generated/10)

RHEL versions currently supported are:
* RHEL7

CentOS versions currently supported are:
* CentOS7


Installation
----------------------
Choose either the CentOS7 or RHEL7 based image:

*  **RHEL7 based image**

    These images are available in the [Red Hat Container Catalog](https://access.redhat.com/containers/#/registry.access.redhat.com/rhscl/postgresql-10-rhel7).
    To download it run:
    ```
    docker pull registry.access.redhat.com/rhscl/postgresql-10-rhel7
    ```

    To build a RHEL7 based image, you need to run Docker build on a properly
    subscribed RHEL machine.

    ```
    $ git clone --recursive https://github.com/sclorg/postgresql-container.git
    $ cd postgresql
    $ make build TARGET=rhel7 VERSIONS=10
    ```

*  **CentOS7 based image**

    These images are available on DockerHub. To download it run:

    ```
    $ docker pull centos/postgresql-10-centos7
    ```

    To build a PostgreSQL image from scratch run:

    ```
    $ git clone --recursive https://github.com/sclorg/postgresql-container.git
    $ cd postgresql
    $ make build TARGET=centos7 VERSIONS=10
    ```

**Notice: By omitting the `VERSIONS` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**

Contributing
--------------------------------

In this repository [distgen](https://github.com/devexp-db/distgen/) is used for generating Dockerfiles. If you'd like update a Dockerfile, please make changes in specs/multispec.yml and/or Dockerfile.template (or other distgen file) and run `make generate_dockerfiles`.

Usage
---------------------------------

For information about usage of Dockerfile for PostgreSQL 9.5,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/9.5).

For information about usage of Dockerfile for PostgreSQL 9.6,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/9.6).

For information about usage of Dockerfile for PostgreSQL 10,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/10).

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
    $ make test TARGET=rhel7 VERSIONS=10
    ```

*  **CentOS based image**

    ```
    $ cd postgresql
    $ make test TARGET=centos7 VERSIONS=10
    ```
+By using the `TEST_CASE` parameter you can choose a test case subset to be run against the image, eg:

    $ cd postgresql
    $ make test VERSIONS=10 TEST_CASE="run_general_tests run_replication_test"


**Notice: By omitting the `VERSIONS` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**
