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

docker exec -i "$CID" container-entrypoint psql -tA < "$pagila_file" &>/dev/null
