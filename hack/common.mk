SKIP_SQUASH?=0

build = hack/build.sh

ifeq ($(TARGET),rhel7)
	OS := rhel7
else
	OS := centos7
endif

tests = $(shell hack/run_test --list 2>/dev/null)

script_env = \
	TEST_CASE="$(TEST_CASE)"                        \
	SKIP_SQUASH=$(SKIP_SQUASH)                      \
	UPDATE_BASE=$(UPDATE_BASE)                      \
	VERSIONS="$(VERSIONS)"                          \
	OS=$(OS)                                        \
	VERSION="$(VERSION)"                            \
	BASE_IMAGE_NAME=$(BASE_IMAGE_NAME)              \
	OPENSHIFT_NAMESPACES="$(OPENSHIFT_NAMESPACES)"

.PHONY: build
build:
	$(script_env) $(build)

.PHONY: test
test:
	$(script_env) TAG_ON_SUCCESS=$(TAG_ON_SUCCESS) TEST_MODE=true $(build)

.PHONY: runtests
runtests: $(tests)

$(tests):
	@echo Running test: $@;
	VERSION=$(VERSION) IMAGE_NAME=$(IMAGE_NAME) hack/run_test $@;
