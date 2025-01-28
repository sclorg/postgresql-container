# PostgreSQL Container Images

[![Build and push images to Quay.io registry](https://github.com/sclorg/postgresql-container/actions/workflows/build-and-push.yml/badge.svg)](https://github.com/sclorg/postgresql-container/actions/workflows/build-and-push.yml)

Images available on Quay.io are:

- CentOS Stream 9 [postgresql-13](https://quay.io/repository/sclorg/postgresql-13-c9s)
- CentOS Stream 9 [postgresql-15](https://quay.io/repository/sclorg/postgresql-15-c9s)
- Fedora [postgresql-11](https://quay.io/repository/fedora/postgresql-11)
- Fedora [postgresql-12](https://quay.io/repository/fedora/postgresql-12)
- Fedora [postgresql-13](https://quay.io/repository/fedora/postgresql-13)
- Fedora [postgresql-14](https://quay.io/repository/fedora/postgresql-14)
- Fedora [postgresql-15](https://quay.io/repository/fedora/postgresql-15)

This repository provides Dockerfiles for PostgreSQL container images, optimized for use with OpenShift. These images are available in RHEL, Fedora, and CentOS-based variants.

For more information about using these images with OpenShift, please refer to the official [OpenShift Documentation](https://docs.okd.io/latest/openshift_images/using-templates.html).

To contribute to this project, please review [the Contribution Guidelines](https://github.com/sclorg/welcome/blob/master/contribution.md).
For learning more information about concepts used in these container images, see the [Landing page](https://github.com/sclorg/welcome).

## Versions

PostgreSQL versions currently supported are:

- [postgresql-12](https://github.com/sclorg/postgresql-container/tree/master/12)
- [postgresql-13](https://github.com/sclorg/postgresql-container/tree/master/13)
- [postgresql-14](https://github.com/sclorg/postgresql-container/tree/master/14)
- [postgresql-15](https://github.com/sclorg/postgresql-container/tree/master/15)

RHEL versions currently supported are:
- RHEL8
- RHEL9
- RHEL10

CentOS versions currently supported are:
- CentOS Stream 9

## Installation

Choose either the CentOS Stream 9 or RHEL9-based image:

- **RHEL9 based image**

  These images are available in the [Red Hat Container Catalog](https://access.redhat.com/containers/#/registry.access.redhat.com/rhel9/postgresql-13).
  To download the image, execute the following command:

  ```bash
  podman pull registry.redhat.io/rhel9/postgresql-13
  ```

  To build a RHEL9-based image, ensure you run Docker build on a RHEL machine with a valid subscription.

  ```bash
  $ git clone --recursive https://github.com/sclorg/postgresql-container.git
  $ cd postgresql
  $ make build TARGET=rhel9 VERSIONS=13
  ```

- **CentOS Stream 9 based image**

  These images are available on Quay.io. To download the image, execute the following command:

  ```bash
  $ podman pull https://quay.io/repository/sclorg/postgresql-13-c9s
  ```

  To build a PostgreSQL image from scratch, perform the following steps:

  ```bash
  $ git clone --recursive https://github.com/sclorg/postgresql-container.git
  $ cd postgresql
  $ make build TARGET=c9s VERSIONS=13
  ```

Note: While the installation steps utilize `podman`, you can substitute these calls with `docker` with the same arguments.

**Warning: By omitting the `VERSIONS` parameter, the build/test action will be executed on all provided versions of PostgreSQL.**

## Contributing Guidelines

This repository utilizes [distgen](https://github.com/devexp-db/distgen/) for generating image source files. If you are interested in updating a Dockerfile, please modify the relevant sections in the `specs/multispec.yml` file and/or the `Dockerfile.template` (or other distgen files), and then execute `make generate`.

Before you begin, ensure that you have `distgen` installed by running `dg --version`. If `distgen` is not installed on your system, follow the installation guide available at [distgen's GitHub repository](https://github.com/devexp-db/distgen/).
Additionally, for testing purposes, install `go-md2man` from this repository [go-md2man](https://github.com/cpuguy83/go-md2man) or via `dnf install go-md2man`.

To contribute, please follow these steps:

1. Fork the repository
2. Run `git submodule update --init` to download the `common` submodule containing the `common/common.mk` makefile.
3. Implement a new feature or bug fix in the templates (found in the `src` directory) or update values in the `specs/multispec.yml` file.
   - Note: If no changes are made to these directories, file regeneration is not necessary.
4. Regenerate all files by executing `make generate`.
5. Consider running CI tests, as described in the Test section below.
6. Commit the files and generated files in two separated commits with a conventional commit message for each.
7. Open a pull request for review!

## Usage

For detailed information on the usage of specific PostgreSQL Dockerfiles, please refer to the corresponding usage documentation:

- [PostgreSQL 12 Usage Documentation](https://github.com/sclorg/postgresql-container/tree/master/12)
- [PostgreSQL 13 Usage Documentation](https://github.com/sclorg/postgresql-container/tree/master/13)
- [PostgreSQL 14 Usage Documentation](https://github.com/sclorg/postgresql-container/tree/master/14)
- [PostgreSQL 15 Usage Documentation](https://github.com/sclorg/postgresql-container/tree/master/15)

For unsupported versions, you may refer to:

- [PostgreSQL 9.2](https://github.com/sclorg/postgresql-container/blob/f213e5d0/9.2)
- [PostgreSQL 9.4](https://github.com/sclorg/postgresql-container/blob/2ab68e86/9.4)

## Test

This repository includes a testing framework that verifies the basic functionality of the PostgreSQL image. Users can choose to test the image based on RHEL or CentOS Stream.

- **RHEL-based image**

  To test a RHEL9-based PostgreSQL image, ensure you are running the test on a properly subscribed RHEL machine.

  ```bash
  $ cd postgresql
  $ make test TARGET=rhel9 VERSIONS=13
  ```

- **CentOS Stream-based image**

  ```bash
  $ cd postgresql
  $ make test TARGET=c9s VERSIONS=13
  ```

- To run a specific subset of test cases, use the `TESTS` parameter:

  ```bash
  $ cd postgresql
  $ make test VERSIONS=13 TESTS="run_general_tests run_replication_test"
  ```

**Note: By omitting the `VERSIONS` parameter, the build/test action will be performed on all provided versions of PostgreSQL.**

The test command is utilized from the `common` submodule. While it is possible to run `make test-openshift-4`, it is typically not necessary. All commands for the Makefile can be found in `common/Makefile`. The `make test` command will execute all tests required by the CI.

## Enabling SSL/TLS for PostgreSQL container

For comprehensive information and instructions on enabling SSL/TLS, please refer to the `examples/enable-ssl/README.md`.
