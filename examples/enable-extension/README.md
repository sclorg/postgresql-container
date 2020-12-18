Extending PostgreSQL image by enabling extension
================================================

This is an example how to use the feature of extending the image (see more at https://github.com/sclorg/postgresql-container/tree/generated/12#extending-image) to enable extension `pg_stat_statements`.

To use this in a Dockerfile, run:

```
podman build . -t my_postgresql:12
```

Then, run the resulting image as usually:

```
podman run -d -e POSTGRESQL_ADMIN_PASSWORD=password my_postgresql:12
```

And see the extension is enabled:
```
podman exec -ti -l bash
bash-4.4$ psql
psql (12.1)
Type "help" for help.

postgres=# \dx
                 List of installed extensions
  Name   | Version |   Schema   |         Description          
---------+---------+------------+------------------------------
 plpgsql | 1.0     | pg_catalog | PL/pgSQL procedural language
(1 row)
```
