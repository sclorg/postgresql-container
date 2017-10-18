# Variables are documented in common/build.sh.
BASE_IMAGE_NAME = postgresql
VERSIONS = 9.4 9.5 9.6
OPENSHIFT_NAMESPACES = 9.2

# HACK:  Ensure that 'git pull' for old clones doesn't cause confusion.
# New clones should use '--recursive'.
.PHONY: $(shell test -f common/common.mk || echo >&2 'Please do "git submodule update --init" first.')

include common/common.mk

# Additional upgrade tests.  Not hooked into CI ATM.
upgrade-tests: $(VERSIONS)
	test/run_upgrade_test 9.2:remote 9.4:local 9.5:local 9.6:local

DG = /usr/bin/dg
DG_EXEC = ${DG} --max-passes 25 --template Dockerfile.template --multispec specs/multispec.yml

generate_dockerfiles:
	for version in ${VERSIONS}; do \
		${DG_EXEC} --distro centos-7-x86_64.yaml --multispec-selector version=$${version} --output $${version}/Dockerfile; \
		${DG_EXEC} --distro rhel-7-x86_64.yaml --multispec-selector version=$${version} --output $${version}/Dockerfile.rhel7; \
	done
