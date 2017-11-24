DEBUG=false

info  () { echo >&2 " * $*" ; }
debug () { ! ${DEBUG} || echo >&2 " ~ $*" ; }
error () { echo >&2 "ERROR: $*" ; false ; }

get_image_id ()
{
    local old_IFS=$IFS
    local result

    # split "$1" into "$1 $2 .." on colons
    IFS=:
    set -- $1
    IFS=$old_IFS
    case $2 in
        local)
            # Default to $IMAGE_NAME if it is set since .image-id might not exist
            echo "${IMAGE_NAME-$(cat "$1"/.image-id)}"
            ;;
        remote)
            local version=${1//\./}
            case $OS in
            rhel7)
                ns=rhscl
                if test "$version" -le 92; then
                    ns=openshift3
                fi
                image=registry.access.redhat.com/$ns/postgresql-${version}-rhel7
                ;;
            centos7)
                ns=centos
                if test "$version" -le 92; then
                    ns=openshift
                fi
                local image=docker.io/$ns/postgresql-${1//\./}-centos7
                ;;
            esac
            docker pull "$image" >/dev/null
            echo "$image"
            ;;
    esac
}

data_pagila_create ()
{
    debug "initializing pagila database"
    CID="$CID" ./test/pagila.sh
}

data_pagila_check ()
{
    debug "doing pagila check"
    local exp_output='28
16
2'
    local output=$(docker exec -i "$CID" container-entrypoint psql -tA <<EOF
select count(*) from information_schema.tables where table_schema = 'public';
select count(*) from information_schema.triggers;
select count(*) from staff;
EOF
)
    test "$exp_output" = "$output" \
        || error "Unexpected output: '$output', expected: '$exp_output'"
}

data_empty_create ()
{
    docker exec -i "$CID" container-entrypoint psql &>/dev/null <<EOF
create table blah (id int);
insert into blah values (1), (2), (3);
EOF
}

data_empty_check ()
{
    debug "doing empty check"
    local exp_output='1
2
3'
    local output=$(docker exec -i "$CID" container-entrypoint psql -tA <<EOF
select * from blah order by id;
EOF
)
    test "$exp_output" = "$output" || error "Unexpected output '$output'"
}

# wait_for_postgres CID
wait_for_postgres ()
{
    local cid=$1
    local stop_after=${2-30}
    local counter=0

    debug "Waiting for PG server to come up in $cid container"
    while test $counter -lt "$stop_after"
    do
        # the "-h localhost" is crucial here as the container runs postgresql
        # server twice and we don't want to connect to the first process (see
        # run-postgresql script)
        output=$(docker exec -i "$cid" bash -c \
            "psql -h localhost -tA -c 'select 1;' 2>/dev/null || :")
        case $output in
        1*) return ;;
        "") ;;
        *) echo "$output" ; false ;;
        esac
        sleep 1
        counter=$(( counter + 1 ))
    done
}


# version2number VERSION [DEPTH] [WIDTH]
# --------------------------------------
version2number ()
{
    local old_IFS=$IFS
    local to_print= depth=${2-3} width=${3-2} sum=0 one_part
    IFS='.'
    set -- $1
    while test $depth -ge 1; do
        depth=$(( depth - 1 ))
        part=${1-0} ; shift || :
        printf "%0${width}d" "$part"
    done
    IFS=$old_IFS
}

# container_ip CONTAINER_ID
# -------------------------
container_ip()
{
  docker inspect --format='{{.NetworkSettings.IPAddress}}' "$1"
}

# vi: set ft=sh
