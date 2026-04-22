import re

from conftest import VARS, create_and_wait_for_container, build_s2i_app


class TestPostgreSQLS2ISSLContainer:
    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = build_s2i_app(app_path=VARS.TEST_DIR / "examples" / "enable-ssl")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()

    def test_ssl(self):
        """
        Test SSL.
        """
        cid_ssl_name = "enable-ssl-test"
        admin_password = "password"
        _, ssl_cip = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_ssl_name,
            container_args=[
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
            ],
            command="",
        )
        assert self.db.db_lib.assert_login_access(
            container_ip=ssl_cip,
            username="postgres",
            password=admin_password,
            database="postgres",
            expected_success=True,
        )

        output = self.db.db_lib.postgresql_cmd(
            container_ip=ssl_cip,
            container_id=VARS.IMAGE_NAME,
            username="postgres",
            password=admin_password,
            database="postgres",
            uri_params={"sslmode": "require"},
            sql_command="-At -c 'SELECT 1;'",
        )
        assert "1" in output


class TestPostgreSQLS2IBakeDataContainer:
    def setup_method(self):
        """
        Setup the test environment.
        """
        self.db = build_s2i_app(app_path=VARS.TEST_DIR / "examples" / "s2i-dump-data")

    def teardown_method(self):
        """
        Teardown the test environment.
        """
        self.db.cleanup()

    def test_ssl(self):
        """
        Test SSL.
        """
        cid_ssl_name = "bake-data-test"
        admin_password = "password"
        _, ssl_cip = create_and_wait_for_container(
            db=self.db,
            cid_file_name=cid_ssl_name,
            container_args=[
                f"-e POSTGRESQL_ADMIN_PASSWORD={admin_password}",
            ],
            command="",
        )
        assert self.db.db_lib.assert_login_access(
            container_ip=ssl_cip,
            username="postgres",
            password=admin_password,
            database="postgres",
            expected_success=True,
        )

        output = self.db.db_lib.postgresql_cmd(
            container_ip=ssl_cip,
            container_id=VARS.IMAGE_NAME,
            username="postgres",
            password=admin_password,
            database="postgres",
            sql_command="-At -c 'SELECT * FROM test;'",
        )
        assert re.search(r"hello world", output), f"hello world not found in {output}"
