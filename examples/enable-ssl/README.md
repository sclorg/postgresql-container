# Enabling SSL/TLS for PostgreSQL container

This example demonstrates extending the PostgreSQL container by enabling SSL/TLS.

## Initial configuration

In this example, we will assume that you are using OpenShift. Suppose you do not have Openshift enabled or installed. In that case, you can install it on RHEL via the tutorial [here](https://docs.openshift.com/container-platform/4.12/installing/index.html) or on Fedora with `dnf install origin-clients` ([Openshift Fedora Developer](https://developer.fedoraproject.org/deployment/ocopenshift/about.html)) and `dnf install podman-docker`. You also need to have a valid KUBECONFIG file.

## Example of how to enable SSL to PostgreSQL

1. Deploy postgres:
   You should use your configuration for `myUser`, `myPassword` and `myDB`

```bash
oc new-app --name psql-ssl postgresql:13-el7~https://github.com/sclorg/postgresql-container.git \
  --context-dir examples/enable-ssl \
  -e POSTGRESQL_USER=myUser \
  -e POSTGRESQL_PASSWORD=myPassword \
  -e POSTGRESQL_DATABASE=myDB
```

2. Create your secrets:

```bash
openssl genrsa -out tls.key 2048
openssl req -new -x509 -key tls.key -out tls.cert
oc create secret tls db-ssl-keys --key tls.key --cert tls.cert
```

3. Bind your secrets into postgres deploymentConfig:

```bash
oc set volume --add \
    --type=secret \
    --secret-name=db-ssl-keys \
    --default-mode=0640 \
    --mount-path=/opt/app-root/src/certs/ \
    dc/psql-ssl
```
