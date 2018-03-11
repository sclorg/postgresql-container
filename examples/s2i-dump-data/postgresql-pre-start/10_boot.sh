if test ! -f "$PGDATA/postgresql.conf"; then
    tar xf "$APP_DATA"/src/data.tar.xz -C "$PGDATA"
fi
