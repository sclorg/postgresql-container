#!/bin/bash

# Postgresql server will reject key files with liberal permissions
# This might fail in OpenShift when using a restricted SCC
# Make sure to run this deployment with an OpenShift service account using  the anyuid SCC
chmod og-rwx certs/tls.key
