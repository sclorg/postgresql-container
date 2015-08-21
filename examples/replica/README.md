# PostgreSQL Replication Example

**WARNING: This is only a Proof-Of-Concept example and it is not meant to be used in
production. Use at your own risk.**

## What is PostgreSQL replication?

Replication enables data from one database server (master, or primary) to be
replicated to one or more servers (slaves, or standby servers).

PostgreSQL has [different replication solutions](http://www.postgresql.org/docs/9.2/static/different-replication-solutions.html),
each with its own pros and cons.
This example uses PostgreSQL's native support for [streaming replication](http://www.postgresql.org/docs/9.2/static/warm-standby.html).
In this configuration, the primary server operates in continuous archiving mode,
while each standby server operates in continuous recovery mode, streaming over
the network the write-ahead log (WAL) records from the primary as they're
generated.

This configuration can be used to create a high availability (HA) cluster
configuration and has relatively low performance impact on the primary server.

A standby server can also be used for read-only queries.

## Deployment

This example uses a [PersistentVolumeClaim](https://docs.openshift.org/latest/architecture/additional_concepts/storage.html#persistent-volume-claims)
to request persistent storage for the primary PostgreSQL server.

You need to have persistent volumes configured and available in your project in
order to continue. For trying out this example in a single node testing
environment, you can create a temporary volume with:

```
$ oc create -f - <<EOF
{
  "kind": "PersistentVolume",
  "apiVersion": "v1",
  "metadata": {
    "name": "postgres-data-volume"
  },
  "spec": {
    "capacity": {
      "storage": "512Mi"
    },
    "hostPath": {
      "path": "`mktemp -d --tmpdir pg-data.XXXXX | tee >(xargs chmod a+rwx)`"
    },
    "accessModes": [
      "ReadWriteOnce"
    ]
  }
}
EOF
```

It is recommended, however, that you use other [type of PersistentVolume](https://docs.openshift.org/latest/architecture/additional_concepts/storage.html#types-of-persistent-volumes)
such as NFS.

Now you can create a new database deployment:

```
$ oc new-app examples/replica/postgresql_replica.json
```

## How does this example work?

### Services 'postgresql-master' and 'postgresql-slave'

These services are the entry point for connecting to, respectively, the primary
database server and any of the standby servers.

In your application, connect to the `postgresql-master` service for write operations, and to `postgresql-master` or `postgresql-slave` for reads.
Keep in mind that reading from a slave might return slightly outdated data.

To get a list of endpoints for the read-only standby servers, you can do a DNS
query. From a container in the same OpenShift project:

```
$ dig postgresql-slave A +search +short
```

### DeploymentConfig 'postgresql-master'

This resource defines a [deployment configuration](https://docs.openshift.org/latest/architecture/core_concepts/deployments.html#deployments-and-deployment-configurations)
to spawn the PostgreSQL primary database server, or master.

Once the master is started, it works as a standalone database server, fully
independent  of the slaves.

### DeploymentConfig 'postgresql-slave'

This resource defines a [deployment configuration](https://docs.openshift.org/latest/architecture/core_concepts/deployments.html#deployments-and-deployment-configurations)
to spawn PostgreSQL standby servers, the slaves.

Upon startup, each slave waits for the master server to become available (via
DNS lookup). Once that happens, the slave connects to the master and starts
streaming the WAL.

To check that the slave is connected and streaming changes from the master,
you can issue the following commands:

```
$ master_name=`oc get pods -l name=postgresql-master -t '{{ (index .items 0).metadata.name }}'`
$ oc exec $master_name -- bash -c 'psql -c "select client_addr, state from pg_stat_replication;"'
```

After a successful deployment, you should get an output similar to:

```
 client_addr  |   state
--------------+-----------
 172.17.0.227 | streaming
(1 row)
```

## Scaling

By default, the provided template creates one primary and one standby server.
Scaling in this setup means increasing the number of standby servers,
consequently increasing data redundancy and concurrent read throughput (if
reading from slaves).

You can add more slaves using `oc scale`:

```
$ oc scale dc postgresql-slave --replicas=2
```

Using `oc scale` with `postgresql-master` is not supported.

After scaling, you can verify that all slaves are streaming changes from the
master with:

```
$ oc exec $master_name -- bash -c 'psql -c "select client_addr, state from pg_stat_replication;"'
 client_addr  |   state
--------------+-----------
 172.17.0.227 | streaming
 172.17.0.229 | streaming
(2 rows)
```

There should be one row per slave (number of replicas defined via `oc scale`).

## Changing passwords

You can change the passwords for the database user and admin, as well as the
password used for replication, by changing the appropriate environment variables
in the deployment configurations described earlier.
No other method is supported.

On every deploy, passwords are reset to match the values in the environment
variables of the DeploymentConfig 'postgresql-master'.

### POSTGRESQL_PASSWORD and POSTGRESQL_ADMIN_PASSWORD

These are, respectively, the passwords for the regular database user defined
by `POSTGRESQL_USER` and the admin user 'postgres'.

You can change these passwords with:

```
$ oc env dc postgresql-master POSTGRESQL_PASSWORD=NewPassword POSTGRESQL_ADMIN_PASSWORD=NewAdminPassword
deploymentconfigs/postgresql-master
```

This will trigger the redeployment of the primary server.
Note that you can change one password but not the other by simply omitting one
of the arguments to `oc env` above.

You can verify that the new password is in effect with:

```
$ oc exec $master_name -- bash -c 'PGPASSWORD=NewPassword psql -h postgresql-master $POSTGRESQL_DATABASE $POSTGRESQL_USER -c "select * from (select inet_server_addr()) ra cross join (select current_database()) cdb cross join (select current_user) cu"'
 inet_server_addr | current_database | current_user
------------------+------------------+--------------
 172.17.1.38      | userdb           | user
(1 row)
```

You should also be able to connect to a slave using the new password:

```
$ oc exec $master_name -- bash -c 'PGPASSWORD=NewPassword psql -h postgresql-slave $POSTGRESQL_DATABASE $POSTGRESQL_USER -c "select * from (select inet_server_addr()) ra cross join (select current_database()) cdb cross join (select current_user) cu"'
 inet_server_addr | current_database | current_user
------------------+------------------+--------------
 172.17.1.35      | userdb           | user
(1 row)
```

For completeness, here's how to verify the new admin password:

```
$ oc exec $master_name -- bash -c 'PGPASSWORD=NewAdminPassword psql -h postgresql-master $POSTGRESQL_DATABASE -c "select * from (select inet_server_addr()) ra cross join (select current_database()) cdb cross join (select current_user) cu"'
 inet_server_addr | current_database | current_user
------------------+------------------+--------------
 172.17.1.38      | userdb           | postgres
(1 row)
```

```
$ oc exec $master_name -- bash -c 'PGPASSWORD=NewAdminPassword psql -h postgresql-slave $POSTGRESQL_DATABASE -c "select * from (select inet_server_addr()) ra cross join (select current_database()) cdb cross join (select current_user) cu"'
 inet_server_addr | current_database | current_user
------------------+------------------+--------------
 172.17.1.35      | userdb           | postgres
(1 row)
```

### POSTGRESQL_MASTER_PASSWORD

This password is used by standby servers to connect to the primary. Both
deployment configurations in this example setup need to agree on the value of
this password to have replication working correctly.

You can change the environment variable with the password on both deployment
configurations at once:

```
$ oc env dc postgresql-master postgresql-slave POSTGRESQL_MASTER_PASSWORD=NewReplicationPassword
deploymentconfigs/postgresql-master
deploymentconfigs/postgresql-slave
```

This will trigger the redeployment of both primary and standby servers.

Note that, as a current limitation in this example, the standby servers store
replicated data in an an ephemeral [emptyDir](https://docs.openshift.org/latest/dev_guide/volumes.html).
This means that redeploying a standby server will cause it to start replicating
again from scratch.

After the primary and standby servers are ready, you can verify that the standby
servers are successfully connected to the primary:

```
$ oc exec $master_name -- bash -c 'psql -c "select client_addr, state from pg_stat_replication;"'
 client_addr |   state
-------------+-----------
 172.17.1.35 | streaming
(1 row)
```
