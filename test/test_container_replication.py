import re

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.database import DatabaseWrapper

from conftest import VARS


class TestPostgreSQLReplicationContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.replication_db = ContainerTestLib(
            image_name=VARS.IMAGE_NAME, db_type="postgresql"
        )
        self.db_wrapper_api = DatabaseWrapper(
            image_name=VARS.IMAGE_NAME, db_type="postgresql"
        )

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.replication_db.cleanup()

    def test_replication(self):
        """
        Test replication.
        """
        database = "postgres"
        master_user = "master"
        master_password = "master"
        master_hostname = "postgresql-master"

        cluster_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=pass",
            f"-e POSTGRESQL_MASTER_USER={master_user}",
            f"-e POSTGRESQL_MASTER_PASSWORD={master_password}",
        ]
        master_cid_name = "master-basic"
        # Run the PostgreSQL master
        assert self.replication_db.create_container(
            cid_file_name=master_cid_name,
            docker_args=cluster_args,
            command="run-postgresql-master",
        )
        # Run the PostgreSQL replica
        master_cip = self.replication_db.get_cip(cid_file_name=master_cid_name)
        assert master_cip
        master_cid = self.replication_db.get_cid(cid_file_name=master_cid_name)
        assert master_cid
        cluster_args += [
            f"--add-host {master_hostname}:{master_cip}",
            f"-e POSTGRESQL_MASTER_IP={master_hostname}",
        ]
        slave_cid_name = "slave-basic-1"
        assert self.replication_db.create_container(
            cid_file_name=slave_cid_name,
            docker_args=cluster_args,
            command="run-postgresql-slave",
        )
        slave_cip = self.replication_db.get_cip(cid_file_name=slave_cid_name)
        assert slave_cip
        slave_cid = self.replication_db.get_cid(cid_file_name=slave_cid_name)
        assert slave_cid
        output = self.db_wrapper_api.run_sql_command(
            container_ip=master_cip,
            username=master_user,
            password=master_password,
            database=database,
            sql_cmd="-c 'select client_addr from pg_stat_replication;'",
            ignore_error=True,
            expected_output=f"{slave_cip}",
        )
        assert slave_cip in output, (
            f"Replica {slave_cip} not found in MASTER {master_cip}"
        )
        # Test the replication
        table_name = "t1"
        value = 24
        output = self.db_wrapper_api.run_sql_command(
            container_ip=master_cip,
            username=master_user,
            password=master_password,
            database=database,
            sql_cmd=f"-c 'CREATE TABLE {table_name} (a integer); INSERT INTO {table_name} VALUES ({value});'",
            expected_output="INSERT 0 1",
        )
        output = self.db_wrapper_api.run_sql_command(
            container_ip=slave_cip,
            username=master_user,
            password=master_password,
            database=database,
            sql_cmd=f"-At -c 'select * from {table_name};'",
            expected_output=f"{value}",
        )
        assert re.search(f"{value}", output), (
            f"Value {value} not found in REPLICA {slave_cip} for table {table_name}"
        )
