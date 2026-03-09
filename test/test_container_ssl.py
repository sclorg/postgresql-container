import re

from pathlib import Path

from container_ci_suite.container_lib import ContainerTestLib
from container_ci_suite.engines.database import DatabaseWrapper

from conftest import VARS


def build_s2i_app(app_path: Path) -> ContainerTestLib:
    container_lib = ContainerTestLib(image_name=VARS.IMAGE_NAME, db_type="postgresql")
    app_name = app_path.name
    s2i_app = container_lib.build_as_df(
        app_path=app_path,
        s2i_args="--pull-policy=never",
        src_image=VARS.IMAGE_NAME,
        dst_image=f"{VARS.IMAGE_NAME}-{app_name}",
    )
    return s2i_app


class TestPostgreSQLS2ISSLContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.ssl_db = build_s2i_app(app_path=VARS.TEST_DIR / "examples" / "enable-ssl")
        self.ssl_db.db_lib.db_type = "postgresql"
        self.dw_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.ssl_db.cleanup()

    def test_ssl(self):
        """
        Test SSL.
        """
        cid_ssl_name = "enable-ssl-test"
        admin_password = "password"

        assert self.ssl_db.create_container(
            cid_file_name=cid_ssl_name,
            docker_args=[
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
            ],
        )
        assert self.dw_api.wait_for_database(
            container_id=self.ssl_db.get_cid(cid_file_name=cid_ssl_name),
            command="/usr/libexec/check-container",
        )
        ssl_cip = self.ssl_db.get_cip(cid_file_name=cid_ssl_name)
        assert ssl_cip
        assert self.dw_api.assert_login_access(
            container_ip=ssl_cip,
            username="postgres",
            password=admin_password,
            database="postgres",
            expected_success=True,
        )

        output = self.dw_api.postgresql_cmd(
            container_ip=ssl_cip,
            container_id=VARS.IMAGE_NAME,
            username="postgres",
            password=admin_password,
            database="postgres?sslmode=require",
            sql_command="-At -c 'SELECT 1;'",
        )
        assert re.search(r"1", output), f"1 not found in {output}"


class TestPostgreSQLS2IBakeDataContainer:
    """
    Test PostgreSQL container configuration.
    """

    def setup_method(self):
        """
        Setup the test environment.
        """
        self.ssl_db = build_s2i_app(
            app_path=VARS.TEST_DIR / "examples" / "s2i-dump-data"
        )
        self.ssl_db.db_lib.db_type = "postgresql"
        self.dw_api = DatabaseWrapper(image_name=VARS.IMAGE_NAME, db_type="postgresql")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.ssl_db.cleanup()

    def test_ssl(self):
        """
        Test SSL.
        """
        cid_ssl_name = "bake-data-test"
        admin_password = "password"

        assert self.ssl_db.create_container(
            cid_file_name=cid_ssl_name,
            docker_args=[
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
            ],
        )
        assert self.dw_api.wait_for_database(
            container_id=self.ssl_db.get_cid(cid_file_name=cid_ssl_name),
            command="/usr/libexec/check-container",
        )
        ssl_cip = self.ssl_db.get_cip(cid_file_name=cid_ssl_name)
        assert ssl_cip
        assert self.dw_api.assert_login_access(
            container_ip=ssl_cip,
            username="postgres",
            password=admin_password,
            database="postgres",
            expected_success=True,
        )

        output = self.dw_api.postgresql_cmd(
            container_ip=ssl_cip,
            container_id=VARS.IMAGE_NAME,
            username="postgres",
            password=admin_password,
            database="postgres",
            sql_command="-At -c 'SELECT * FROM test;'",
        )
        assert re.search(r"hello world", output), f"hello world not found in {output}"
