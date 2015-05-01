# PostgreSQL Replication Example

**WARNING:**

**This is only a Proof-Of-Concept example and it is not meant to be used in any
production. Use at your own risk.**

## What is PostgreSQL replication?

Replication enables data from one PostgreSQL database server (the master) to be
replicated to one or more PostgreSQL database servers (the slaves). Replication is asynchronous - slaves do not need not be connected permanently to receive updates from the master. This means that updates can occur over long-distance connections and even over temporary or intermittent connections such as a dial-up service.  Depending on the configuration, you can replicate all databases, selected databases, or even selected tables within a database.


## How does this example work?

The provided JSON file (`postgres_replica.json`) contains a `Config` resource that groups the Kubernetes and OpenShift resources which are meant to be created.  
### Service 'pg-master'

This resource provides Service for the PostgreSQL server which acts as the 'master'. 


### Service 'pg-slave'

This provides a Service for the PostgreSQL servers that the master uses as 'slaves' which are used to replicate the data from the PostgreSQL master.

In this case, you can query the DNS (eg. `dig pg-standby A +search +short`) to
obtain the list of the Service endpoints (the PostgreSQL servers that subscribe to this service).

### ReplicationController 'pg-master'

This resource defines the `PodTemplate` of the PostgreSQL server that acts as the 'master'. The Pod uses the `openshift/postgresql-92-centos7` image.  Once the PostgreSQL master server is started, it has no slaves preconfigured as the slaves registers automatically.  To check that the master PostgreSQL server is working, you can issue the following command on the master container:

```
psql -h pg-master.foo.local -U user -W db 
psql> select * from pg_stat_replication;
```

### ReplicationController 'pg-slave'

This resource defines the `PodTemplate` of the PostgreSQL servers that act as the `slaves` to the `master` server. In the provided JSON example, this Replication Controller starts with 2 slaves. Each `slave` server first waits for the `master` server to become available (getting the `master` server IP using the DNS lookup). Once the `master` is available, the PostgreSQL 'slave' server is started and connected to the `master`. 

To check the 'slave' status, you can issue the following command on the slave container:

```
psql -h pg-standby.default.local -U user -W db 
```

You can add more slaves if you want, using the following `osc` command.

```
$ osc update rc pg-slave --patch='{ "apiVersion": "v1beta1", "desiredState": { "replicas": 3 }}'
```
