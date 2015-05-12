#!/bin/bash -e
# $1 - Specifies distribution - RHEL7/CentOS7
# $2 - Specifies PostgreSQL version - 9.2
# TEST_MODE - If set, build a candidate image and test it

# Array of all versions of PostgreSQL
declare -a VERSIONS=(9.2)

OS=$1
VERSION=$2

function squash { 
  # install the docker layer squashing tool
  easy_install --user docker-scripts==0.3.3
  base=$(awk '/^FROM/{print $2}' Dockerfile)
  $HOME/.local/bin/docker-scripts squash -f $base ${IMAGE_NAME}
}

# TODO: Remove once docker 1.5 is in usage (support for named Dockerfiles)
function docker_build() {
	TAG=$1
	DOCKERFILE=$2

	if [ -n "$DOCKERFILE" -a "$DOCKERFILE" != "Dockerfile" ]; then
		# Swap Dockerfiles and setup a trap restoring them
		mv Dockerfile Dockerfile.centos7
		mv "${DOCKERFILE}" Dockerfile
		trap "mv Dockerfile ${DOCKERFILE} && mv Dockerfile.centos7 Dockerfile" ERR RETURN
	fi

	docker build -t ${TAG} . && trap - ERR
	squash
}

if [ -z ${VERSION} ]; then
	# Build all versions
	dirs=${VERSIONS}
else
	# Build only specified version on PostgreSQL
	dirs=${VERSION}
fi

for dir in ${dirs}; do
	IMAGE_NAME=openshift/postgresql-${dir//./}-${OS}
	if [ -v TEST_MODE ]; then
		IMAGE_NAME="${IMAGE_NAME}-candidate"
	fi
	echo ">>>> Building ${IMAGE_NAME}"

	pushd ${dir} > /dev/null

	if [ "$OS" == "rhel7" ]; then
		docker_build ${IMAGE_NAME} Dockerfile.rhel7
	else
		docker_build ${IMAGE_NAME}
	fi

	if [ -v TEST_MODE ]; then
		IMAGE_NAME=${IMAGE_NAME} test/run
	fi

 	popd > /dev/null
done
