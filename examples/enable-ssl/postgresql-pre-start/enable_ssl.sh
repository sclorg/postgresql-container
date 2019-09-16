#!/bin/bash

# Postgresql server will reject key files with liberal permissions
chmod og-rwx server.key
