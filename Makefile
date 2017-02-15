# Variables are documented in common/build.sh.
BASE_IMAGE_NAME = postgresql
VERSIONS = 9.4 9.5
OPENSHIFT_NAMESPACES = 9.2

# HACK:  Ensure that 'git pull' for old clones doesn't cause confusion.
# New clones should use '--recursive'.
.PHONY: $(shell test -f common/common.mk || echo >&2 'Please do "git submodule update --init" first.')

include common/common.mk
