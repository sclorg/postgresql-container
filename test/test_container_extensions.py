import re
import os
import tempfile

from time import sleep
from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.container_lib import ContainerTestLibUtils
from container_ci_suite.engines.database import DatabaseWrapper
from container_ci_suite.engines.podman_wrapper import PodmanCLIWrapper
from container_ci_suite.utils import get_file_content

import pytest

from conftest import VARS, create_postgresql_volume_dir


class TestPostgreSQLPluginContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type="postgresql")
        self.db_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()

    @pytest.mark.parametrize(
        "env_load",
        [
            (""),
            ("-e POSTGRESQL_EXTENSIONS=pgaudit -e POSTGRESQL_LIBRARIES=pgaudit"),
        ],
    )
    def test_pgaudit_extension_installation(self, env_load):
        """
        Test pogaudit installation.
        """
        if VARS.VERSION in ["9.6", "10", "11"]:
            pytest.skip("pgaudit not expected, test skipped.")
        cid_file_name = "test_pg_pgaudit"
        config_dir = tempfile.mkdtemp(prefix="/tmp/psql-pgaudit-volume")
        sql_cmd1 = "SET pgaudit.log = 'read, ddl';\nCREATE DATABASE pgaudittest;"
        sql_cmd2 = "SET pgaudit.log = 'read, ddl';\nCREATE TABLE account \
            (id int, name text, password text, description text);"
        sql_cmd3 = "INSERT INTO account (id, name, password, description) \
            VALUES (1, 'user1', 'HASH1', 'blah, blah');\nSELECT * FROM account;"
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -R -m u:26:rwx {config_dir}",
                f"cp -r {VARS.TEST_DIR}/examples/pgaudit/* {config_dir}/",
                f"setfacl -R -m u:26:rwx {config_dir}",
                f"echo '{sql_cmd1}' > {config_dir}/enable-extension.sql",
                f"echo '{sql_cmd2}' > {config_dir}/insert-data.sql",
                f"echo '{sql_cmd3}' >> {config_dir}/insert-data.sql",
                f"cat {config_dir}/enable-extension.sql",
                f"cat {config_dir}/insert-data.sql",
            ]
        )
        volume_dir = create_postgresql_volume_dir()
        docker_args = [
            env_load,
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            f"-v {config_dir}:/opt/app-root/src:Z",
            f"-v {volume_dir}:/var/lib/pgsql/data:Z",
        ]

        assert self.db.create_container(
            cid_file_name=cid_file_name,
            docker_args=docker_args,
            command="",
        )
        cip = self.db.get_cip(cid_file_name=cid_file_name)
        assert cip
        cid = self.db.get_cid(cid_file_name=cid_file_name)
        assert cid
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd='psql -tA -c "SHOW shared_preload_libraries;"',
        )
        assert "pgaudit" in output, (
            f"pgaudit should be in the shared_preload_libraries, but is {output}"
        )
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.call_podman_command(
            cmd=f'exec {cid} bash -c "psql < /opt/app-root/src/enable-extension.sql"',
        )
        output = PodmanCLIWrapper.call_podman_command(
            cmd=f'exec {cid} bash -c "psql < /opt/app-root/src/insert-data.sql"',
        )
        sleep(1)
        log_files_to_check = []
        for f in os.listdir(Path(volume_dir) / "userdata" / "log"):
            if f.startswith("postgresql-"):
                log_files_to_check.append(Path(volume_dir) / "userdata" / "log" / f)
        for f in log_files_to_check:
            output = get_file_content(
                filename=f,
            )
        words_to_check = [
            "AUDIT: SESSION,.*,.*,DDL,CREATE DATABASE,,,CREATE DATABASE pgaudittest",
            "AUDIT: SESSION,.*,.*,READ,SELECT,,,SELECT",
        ]
        for word in words_to_check:
            assert re.search(word, output), (
                f"{word} should be in the output, but is {output}"
            )

    def test_pgvector(self):
        """
        Test pgvector installation.
        """
        if VARS.VERSION in ["11", "12", "13", "15"]:
            pytest.skip("pgvector not expected on this version, test skipped.")
        if VARS.OS == "rhel8":
            pytest.skip("pgvector not expected on this OS, test skipped.")
        cid_file_name = "test_pg_pgvector"
        config_dir = tempfile.mkdtemp(prefix="/tmp/psql-pgvector-volume")
        sql_cmd = "CREATE EXTENSION vector;\nCREATE TABLE items (id bigserial PRIMARY KEY, embedding vector(3));"
        ContainerTestLibUtils.commands_to_run(
            commands_to_run=[
                f"setfacl -R -m u:26:rwx {config_dir}",
                f"cp -r {VARS.TEST_DIR}/examples/pgvector/* {config_dir}/",
                f"setfacl -R -m u:26:rwx {config_dir}",
                f"echo '{sql_cmd}' > {config_dir}/enable-vector.sql",
            ]
        )
        volume_dir = create_postgresql_volume_dir()
        docker_args = [
            "-e POSTGRESQL_ADMIN_PASSWORD=password",
            f"-v {config_dir}:/opt/app-root/src:Z",
            f"-v {volume_dir}:/var/lib/pgsql/data:Z",
        ]

        assert self.db.create_container(
            cid_file_name=cid_file_name,
            docker_args=docker_args,
            command="",
        )
        cip = self.db.get_cip(cid_file_name=cid_file_name)
        assert cip
        cid = self.db.get_cid(cid_file_name=cid_file_name)
        assert cid
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.podman_exec_shell_command(
            cid_file_name=cid,
            cmd='psql -tA -c "SHOW shared_preload_libraries;"',
        )
        assert "vector" in output, (
            f"pgaudit should be in the shared_preload_libraries, but is {output}"
        )
        assert self.db_api.wait_for_database(
            container_id=cid, command="/usr/libexec/check-container"
        )
        output = PodmanCLIWrapper.call_podman_command(
            cmd=f'exec {cid} bash -c "psql < /opt/app-root/src/enable-vector.sql"',
        )
        sleep(1)
        assert output
