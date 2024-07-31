# Variables are documented in common/build.sh.
BASE_IMAGE_NAME = postgresql
VERSIONS = 12 13 14 15 16
OPENSHIFT_NAMESPACES = 9.2
NOT_RELEASED_VERSIONS =

# HACK:  Ensure that 'git pull' for old clones doesn't cause confusion.
# New clones should use '--recursive'.
.PHONY: $(shell test -f common/common.mk || echo >&2 'Please do "git submodule update --init" first.')

include common/common.mk

# use clean-versions provided by common.mk
clean-hook: clean-versions

script_env += NOT_RELEASED_VERSIONS="$(NOT_RELEASED_VERSIONS)"
