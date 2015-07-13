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
  easy_install --user docker_py==1.2.3 docker-scripts==0.4.2
  base=$(awk '/^FROM/{print $2}' $1)
  $HOME/.local/bin/docker-scripts squash -f $base ${IMAGE_NAME}
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

  if [ "$OS" == "rhel7" -o "$OS" == "rhel7-candidate" ]; then
    docker build -t ${IMAGE_NAME} -f Dockerfile.rhel7 .
    if [ "${SKIP_SQUASH}" -ne "1" ]; then
      squash Dockerfile.rhel7
    fi
  else
    docker build -t ${IMAGE_NAME} .
    if [ "${SKIP_SQUASH}" -ne "1" ]; then
      squash Dockerfile
    fi
  fi

  if [ -v TEST_MODE ]; then
    IMAGE_NAME=${IMAGE_NAME} test/run
  fi

  popd > /dev/null
done
