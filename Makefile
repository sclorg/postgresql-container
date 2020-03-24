# Variables are documented in common/build.sh.
BASE_IMAGE_NAME = postgresql
VERSIONS = 9.6 10 11 12
OPENSHIFT_NAMESPACES = 9.2
NOT_RELEASED_VERSIONS =

# HACK:  Ensure that 'git pull' for old clones doesn't cause confusion.
# New clones should use '--recursive'.
.PHONY: $(shell test -f common/common.mk || echo >&2 'Please do "git submodule update --init" first.')

include common/common.mk

# use clean-versions provided by common.mk
clean-hook: clean-versions

script_env += NOT_RELEASED_VERSIONS="$(NOT_RELEASED_VERSIONS)"

# Additional upgrade tests.  Not hooked into CI ATM.
upgrade-tests: $(VERSIONS)
	OS=$(OS) test/run_upgrade_test 9.2:remote 9.4:local 9.5:local 9.6:local 10:local

build-serial: generate
test-openshift-remote-cluster: generate
