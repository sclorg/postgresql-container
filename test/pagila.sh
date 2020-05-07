#! /bin/sh

set -e

die() { echo "$*" >&2 ; exit 1; }

test -z "$CID" && die "Please specify \$CID variable"
# test -d common || die "Please run me from git root directory"

pagila_mirror=https://dl.fedoraproject.org/pub/epel/7/x86_64/Packages/p/
pagila_base="pagila-0.10.1-3.el7.noarch.rpm"
pagila=$pagila_mirror$pagila_base
pagila_file="$PWD/postgresql-container-pagila.sql"
pagila_sha256sum=b968d9498d866bff8f47d9e50edf49feeff108d4164bff2aa167dc3eae802701

(
  flock --timeout 180 9

  # Already downloaded?
  test ! -f "$pagila_file" || exit 0

  set -o pipefail
  curl -s "$pagila" > "$pagila_base"
  for file in ./usr/share/pagila/pagila-schema.sql \
      ./usr/share/pagila/pagila-data.sql \
      ./usr/share/pagila/pagila-insert-data.sql ; \
  do
    rpm2cpio "$pagila_base" | cpio --extract --to-stdout "$file"
  done >"$pagila_file"
) 9<"$0"

case $(sha256sum "$pagila_file") in
"$pagila_sha256sum"*) ;;
*) false ;;
esac

# Deliberately using a separate container, otherwise the docker exec with redirection
# does not work in podman 1.6.x due to https://bugzilla.redhat.com/show_bug.cgi?id=1827324
# This change can be reverted to the previous variant, once this BZ is fixed.
server_ip=$(docker inspect --format='{{.NetworkSettings.IPAddress}}' "$CID")
admin_pass=$(docker exec "$CID" bash -c 'echo $POSTGRESQL_ADMIN_PASSWORD')
docker run --rm -i "$IMAGE_NAME" bash -c "PGPASSWORD=$admin_pass psql -h $server_ip" <"$pagila_file" &>/dev/null
