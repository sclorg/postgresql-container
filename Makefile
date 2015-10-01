# Variables are documented in hack/build.sh.
BASE_IMAGE_NAME = postgresql
VERSIONS = 9.2 9.4
OPENSHIFT_NAMESPACES = 9.2

# Include common Makefile code.
include hack/common.mk
