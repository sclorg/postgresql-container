PostgreSQL container images
========================

[![Build and push images to Quay.io registry](https://github.com/sclorg/postgresql-container/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/sclorg/postgresql-container/actions/workflows/build-and-push.yml)

Images available on Quay are:
* CentOS 7 [postgresql-10](https://quay.io/repository/centos7/postgresql-10-centos7)
* CentOS 7 [postgresql-12](https://quay.io/repository/centos7/postgresql-12-centos7)
* CentOS 7 [postgresql-13](https://quay.io/repository/centos7/postgresql-13-centos7)
* CentOS Stream 8 [postgresql-10](https://quay.io/repository/sclorg/postgresql-10-c8s)
* CentOS Stream 8 [postgresql-13](https://quay.io/repository/sclorg/postgresql-13-c8s)
* CentOS Stream 8 [postgresql-15](https://quay.io/repository/sclorg/postgresql-15-c8s)
* CentOS Stream 9 [postgresql-13](https://quay.io/repository/sclorg/postgresql-13-c9s)
* CentOS Stream 9 [postgresql-15](https://quay.io/repository/sclorg/postgresql-15-c9s)
* Fedora [postgresql-11](https://quay.io/repository/fedora/postgresql-11)
* Fedora [postgresql-12](https://quay.io/repository/fedora/postgresql-12)
* Fedora [postgresql-13](https://quay.io/repository/fedora/postgresql-13)
* Fedora [postgresql-15](https://quay.io/repository/fedora/postgresql-15)

This repository contains Dockerfiles for PostgreSQL images for OpenShift.
Users can choose between RHEL, Fedora and CentOS based images.

For more information about using these images with OpenShift, please see the
official [OpenShift Documentation](https://docs.okd.io/latest/openshift_images/using-templates.html).

For more information about contributing, see
[the Contribution Guidelines](https://github.com/sclorg/welcome/blob/master/contribution.md).
For more information about concepts used in these container images, see the
[Landing page](https://github.com/sclorg/welcome).


Versions
---------------
PostgreSQL versions currently supported are:
* [postgresql-10](https://github.com/sclorg/postgresql-container/tree/generated/10)
* [postgresql-12](https://github.com/sclorg/postgresql-container/tree/generated/12)
* [postgresql-13](https://github.com/sclorg/postgresql-container/tree/generated/13)
* [postgresql-15](https://github.com/sclorg/postgresql-container/tree/generated/15)

RHEL versions currently supported are:
* RHEL7
* RHEL8
* RHEL9

CentOS versions currently supported are:
* CentOS7
* CentOS Stream 8
* CentOS Stream 9


Installation
----------------------
Choose either the CentOS Stream 9 or RHEL9 based image:

*  **RHEL9 based image**

    These images are available in the [Red Hat Container Catalog](https://access.redhat.com/containers/#/registry.access.redhat.com/rhel9/postgresql-13).
    To download it run:
    ```
    podman pull registry.redhat.io/rhel9/postgresql-13
    ```

    To build a RHEL9 based image, you need to run Docker build on a properly
    subscribed RHEL machine.

    ```
    $ git clone --recursive https://github.com/sclorg/postgresql-container.git
    $ cd postgresql
    $ make build TARGET=rhel9 VERSIONS=13
    ```

*  **CentOS Stream 9 based image**

    These images are available on Quay.io. To download it run:

    ```
    $ podman pull https://quay.io/repository/sclorg/postgresql-13-c9s
    ```

    To build a PostgreSQL image from scratch run:

    ```
    $ git clone --recursive https://github.com/sclorg/postgresql-container.git
    $ cd postgresql
    $ make build TARGET=c9s VERSIONS=13
    ```

Note: while the installation steps are calling `podman`, you can replace any such calls by `docker` with the same arguments.

**Notice: By omitting the `VERSIONS` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**

Contributing
--------------------------------

In this repository [distgen](https://github.com/devexp-db/distgen/) is used for generating image source files. If you'd like update a Dockerfile, please make changes in specs/multispec.yml and/or Dockerfile.template (or other distgen file) and run `make generate`.

Usage
---------------------------------

For information about usage of Dockerfile for PostgreSQL 10,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/10).

For information about usage of Dockerfile for PostgreSQL 12,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/12).

For information about usage of Dockerfile for PostgreSQL 13,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/13).

For information about usage of Dockerfile for PostgreSQL 15,
see [usage documentation](https://github.com/sclorg/postgresql-container/tree/generated/15).

For versions which are not supported anymore:

* [PostgreSQL 9.2](https://github.com/sclorg/postgresql-container/blob/f213e5d0/9.2)
* [PostgreSQL 9.4](https://github.com/sclorg/postgresql-container/blob/2ab68e86/9.4)

Test
---------------------------------

This repository also provides a test framework, which checks basic functionality
of the PostgreSQL image.

Users can choose between testing PostgreSQL based on a RHEL or CentOS Stream image.

*  **RHEL based image**

    To test a RHEL9 based PostgreSQL image, you need to run the test on a properly
    subscribed RHEL machine.

    ```
    $ cd postgresql
    $ make test TARGET=rhel9 VERSIONS=13
    ```

*  **CentOS Stream based image**

    ```
    $ cd postgresql
    $ make test TARGET=c9s VERSIONS=13
    ```
+By using the `TESTS` parameter you can choose a test case subset to be run against the image, eg:

    $ cd postgresql
    $ make test VERSIONS=13 TESTS="run_general_tests run_replication_test"


**Notice: By omitting the `VERSIONS` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**
