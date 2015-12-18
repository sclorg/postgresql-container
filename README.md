PostgreSQL Docker images
========================

This repository contains Dockerfiles for PostgreSQL images for OpenShift.
Users can choose between RHEL and CentOS based images.

For more information about using these images with OpenShift, please see the
official [OpenShift Documentation](https://docs.openshift.org/latest/using_images/db_images/postgresql.html).

Versions
---------------
PostgreSQL versions currently provided are:
* postgresql-9.2
* postgresql-9.4

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
    $ git clone https://github.com/openshift/postgresql.git
    $ cd postgresql
    $ make build TARGET=rhel7 VERSION=9.4
    ```

*  **CentOS7 based image**

    This image is available on DockerHub. To download it run:

    ```
    $ docker pull openshift/postgresql-92-centos7
    ```

    To build a PostgreSQL image from scratch run:

    ```
    $ git clone https://github.com/openshift/postgresql.git
    $ cd postgresql
    $ make build VERSION=9.2
    ```

**Notice: By omitting the `VERSION` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**


Usage
---------------------------------

For information about usage of Dockerfile for PostgreSQL 9.2,
see [usage documentation](9.2/README.md).

For information about usage of Dockerfile for PostgreSQL 9.4,
see [usage documentation](9.4/README.md).


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
    $ make test TARGET=rhel7 VERSION=9.2
    ```

*  **CentOS based image**

    ```
    $ cd postgresql
    $ make test VERSION=9.2
    ```

**Notice: By omitting the `VERSION` parameter, the build/test action will be performed
on all provided versions of PostgreSQL.**
