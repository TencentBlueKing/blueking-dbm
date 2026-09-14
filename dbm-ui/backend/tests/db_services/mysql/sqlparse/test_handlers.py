# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import pytest

from backend.db_services.mysql.sqlparse.exceptions import SQLParseBaseException
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler


class TestSQLParseHandler:
    @staticmethod
    def test_select_for_update():
        sql = "select * from goods where id = 1 and name='prod11' for update;"
        result = SQLParseHandler().parse_sql(sql)
        assert result == {
            "command": "SELECT,UPDATE",
            "query_string": "select * from goods where id = 1 and name='prod11' for update;",
            "query_digest_text": "select * from goods where id = ? and name = '?' for update ;",
            "query_digest_md5": "cd85202ea8e7e56979472302581b9fa9",
            "table_name": "goods",
            "query_length": 62,
        }

    @staticmethod
    def test_include_punctuation():
        sql = """
        select id,'18;19',age,33454354.453 from actor where
        id='dsadsadsadsadsadsadsadsadads'
        and id2=12321321321
        and dt='2011-10-10';
        """
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select id,'18;19',age,33454354.453 from actor where id='dsadsadsadsadsadsadsadsadads' "
            "and id2=12321321321 and dt='2011-10-10';",
            "query_digest_text": "select id , '?' , age , ? from actor where id = '?' and id2 = ? and dt = '?' ;",
            "query_digest_md5": "49ff4686038156fb7dea8b5b2fe59ce5",
            "table_name": "actor",
            "query_length": 128,
        }

    @staticmethod
    def test_join():
        sql = (
            "select trx_state,p.command,p.state, p.user, max(TIMESTAMPDIFF(SECOND,trx_started,now())) "
            "max_trx_long_time, max(p.time) max_trx_idle_time from  information_schema.innodb_trx t join "
            "information_schema.processlist p on t.trx_mysql_thread_id=p.id group by trx_state,command,state,user;"
        )
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select trx_state,p.command,p.state, p.user, max(TIMESTAMPDIFF(SECOND,trx_started,now()))"
            " max_trx_long_time, max(p.time) max_trx_idle_time from information_schema.innodb_trx t "
            "join information_schema.processlist p on t.trx_mysql_thread_id=p.id group by trx_state,"
            "command,state,user;",
            "query_digest_text": "select trx_state , p . command , p . state , p . user ,"
            " max ( TIMESTAMPDIFF ( SECOND , trx_started , now ( ) ) ) max_trx_long_time , "
            "max ( p . time ) max_trx_idle_time from information_schema . innodb_trx t "
            "join information_schema . processlist p on t . trx_mysql_thread_id = p . id "
            "group by trx_state , command , state , user ;",
            "query_digest_md5": "3d1ebf49578c16081fb1563874177290",
            "table_name": "information_schema.innodb_trx,information_schema.processlist",
            "query_length": 281,
        }

    @staticmethod
    def test_count():
        sql = (
            "select count(*) from  information_schema.INNODB_TRX where  TIMESTAMPDIFF(SECOND,trx_started,now()) > 30;"
        )
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select count(*) from information_schema.INNODB_TRX "
            "where TIMESTAMPDIFF(SECOND,trx_started,now()) > 30;",
            "query_digest_text": "select count ( * ) from information_schema . INNODB_TRX "
            "where TIMESTAMPDIFF ( SECOND , trx_started , now ( ) ) > ? ;",
            "query_digest_md5": "69302d896e1df76238f89e0b2dede003",
            "table_name": "information_schema.INNODB_TRX",
            "query_length": 102,
        }

    @staticmethod
    def test_rename_two_table():
        sql = (
            "select a.ip, b.port from db_meta_machine a, db_meta_storageinstance b "
            "where a.cluster_type='tendbha' and a.access_layer='storage' and a.bk_host_id = b.machine_id;"
        )
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "SELECT",
            "query_string": "select a.ip, b.port from db_meta_machine a, db_meta_storageinstance b where "
            "a.cluster_type='tendbha' and a.access_layer='storage' and a.bk_host_id = b.machine_id;",
            "query_digest_text": "select a . ip , b . port from db_meta_machine a , db_meta_storageinstance b "
            "where a . cluster_type = '?' and a . access_layer = '?' "
            "and a . bk_host_id = b . machine_id ;",
            "query_digest_md5": "60e7cb8bf7ed12639d66a79d8fadff96",
            "table_name": "db_meta_machine,db_meta_storageinstance",
            "query_length": 162,
        }

    @staticmethod
    def test_alert_table():
        sql = "alter table ha_agent_logs add index idx1(agent_ip, ip, port), drop index idx_ins;"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "ALTER,DROP",
            "query_string": "alter table ha_agent_logs add index idx1(agent_ip, ip, port), drop index idx_ins;",
            "query_digest_text": "alter table ha_agent_logs add index idx1 ( agent_ip , ip , port ) , "
            "drop index idx_ins ;",
            "query_digest_md5": "c8ce8c74903d0bd2d723e9cc73f0a364",
            "table_name": "ha_agent_logs",
            "query_length": 81,
        }

    @staticmethod
    def test_create_table():
        sql = "create table tb_instance_version_charset(version text, charset int, engines text);"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "CREATE",
            "query_string": "create table tb_instance_version_charset(version text, charset int, engines text);",
            "query_digest_text": "create table tb_instance_version_charset "
            "( version text , charset int , engines text ) ;",
            "query_digest_md5": "52668e3967eb9ae57d845f97381b0440",
            "table_name": "tb_instance_version_charset",
            "query_length": 82,
        }

    @staticmethod
    def test_drop_table():
        sql = "DROP TABLE tb_instance_version_charset;"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "DROP",
            "query_string": "DROP TABLE tb_instance_version_charset;",
            "query_digest_text": "DROP TABLE tb_instance_version_charset ;",
            "query_digest_md5": "50ba8416364a3a8df59ec446820649bf",
            "table_name": "tb_instance_version_charset",
            "query_length": 39,
        }

    @staticmethod
    def test_truncate_table():
        sql = "TRUNCATE TABLE tb_instance_version_charset;"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "TRUNCATE",
            "query_string": "TRUNCATE TABLE tb_instance_version_charset;",
            "query_digest_text": "TRUNCATE TABLE tb_instance_version_charset ;",
            "query_digest_md5": "421438b35cfc17475a7857b6427e9fd1",
            "table_name": "tb_instance_version_charset",
            "query_length": 43,
        }

    @staticmethod
    def test_insert_into():
        sql = """
         insert into tb_instance_version_charset(ip, port, version, charset, engines, addr, create_at)
          values('127.0.0.1', 20003, '5.5.24-tmysql-1.6-log', 'utf8mb4', 'InnoDB', '127.0.0.1:20003', now());
         """
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "INSERT",
            "query_string": "insert into tb_instance_version_charset(ip, port, version, charset, engines, addr, "
            "create_at) values('127.0.0.1', 20003, '5.5.24-tmysql-1.6-log', 'utf8mb4', 'InnoDB', "
            "'127.0.0.1:20003', now());",
            "query_digest_text": "insert into tb_instance_version_charset ( ip , port , version , charset , engines , "
            "addr , create_at ) values ( '?' , ? , '?' , '?' , '?' , '?' , now ( ) ) ;",
            "query_digest_md5": "6525fca29f39de6e2f7847e6558d9e27",
            "table_name": "tb_instance_version_charset",
            "query_length": 195,
        }

    @staticmethod
    def test_insert_into_with_select():
        # TODO，此 case table name 不对
        sql = """
        INSERT IGNORE INTO gameai_llm_proxy.request_tokens (request_id, create_time)
        SELECT request_id, create_time
        FROM gameai_llm_proxy.request_data;
        """
        print(SQLParseHandler().parse_sql(sql))
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "INSERT,SELECT",
            "query_string": "INSERT IGNORE INTO gameai_llm_proxy.request_tokens (request_id, create_time) "
            "SELECT request_id, create_time FROM gameai_llm_proxy.request_data;",
            "query_digest_text": "INSERT IGNORE INTO gameai_llm_proxy . request_tokens ( request_id , create_time ) "
            "SELECT request_id , create_time FROM gameai_llm_proxy . request_data ;",
            "query_digest_md5": "640fe92d547930b1e7869f514aacd9e3",
            "table_name": "create_time,gameai_llm_proxy.request_data,gameai_llm_proxy.request_tokens,request_id",
            "query_length": 145,
        }

    @staticmethod
    def test_update_data():
        sql = "update db_meta_storageinstance set status='unavailable' where id in (16184,16183);"
        assert SQLParseHandler().parse_sql(sql) == {
            "command": "UPDATE",
            "query_string": "update db_meta_storageinstance set status='unavailable' where id in (16184,16183);",
            "query_digest_text": "update db_meta_storageinstance set status = '?' where id in ( ? , ? ) ;",
            "query_digest_md5": "ca4129d268538e8bd332d6898eca0788",
            "table_name": "db_meta_storageinstance",
            "query_length": 82,
        }

    @staticmethod
    def test_complex_sql():
        """超长 SQL 超过 sqlparse token 上限时返回友好业务异常，而不是库内部错误。"""
        sql = "SELECT " + ", ".join(f"c{i}" for i in range(12000)) + " FROM t"
        with pytest.raises(SQLParseBaseException) as ei:
            SQLParseHandler().parse_sql(sql)
        assert "无法解析" in str(ei.value.message)

    @staticmethod
    def test_sql_select_stat():
        sql_no_limit = """
        SELECT e.employee_id, e.employee_name,
        (SELECT COUNT(*) FROM projects p WHERE p.employee_id = e.employee_id LIMIT 3) AS project_count, e.salary
        FROM employees e
        WHERE e.department_id IN (SELECT department_id FROM departments LIMIT) ORDER BY project_count DESC
        """
        with pytest.raises(SQLParseBaseException):
            SQLParseHandler().parse_select_statement(sql_no_limit)

        sql_no_select = """
        UPDATE employees e
        SET bonus = CASE
            WHEN e.salary > (SELECT AVG(salary) FROM employees WHERE department_id = e.department_id)
            THEN e.bonus * 1.2
            ELSE e.bonus * 1.1
        END
        WHERE e.employee_id IN (SELECT DISTINCT employee_id FROM projects WHERE project_status = 'completed');
        """
        with pytest.raises(SQLParseBaseException):
            SQLParseHandler().parse_select_statement(sql_no_select)

        correct_select_sql = """
        SELECT e.employee_id, e.employee_name,
        FROM employees e
        WHERE e.department_id NOT IN (1,2,3) ORDER BY project_count LIMIT 10
        """
        assert SQLParseHandler().parse_select_statement(correct_select_sql) is None

        banned_select_sql = """
        SELECT user, host
        FROM mysql.user
        WHERE user in ("admin", "test") LIMIT 10
        """
        with pytest.raises(SQLParseBaseException):
            SQLParseHandler().parse_select_statement(banned_select_sql)

        show_sql = """
        SHOW DATABASES;
        """
        assert SQLParseHandler().parse_select_statement(show_sql) is None

        desc_sql = """
        DESCRIBE TABLE1;
        """
        assert SQLParseHandler().parse_select_statement(desc_sql) is None

        show_var_sql1 = """
        SHOW VARIABLES;
        """
        assert SQLParseHandler().parse_select_statement(show_var_sql1) is None

        show_var_sql2 = """
        SHOW VARIABLES LIKE %x;
        """
        assert SQLParseHandler().parse_select_statement(show_var_sql2) is None

        show_tables_sql = """
        SHOW TABLES FORM DBM;
        """
        assert SQLParseHandler().parse_select_statement(show_tables_sql) is None

        show_processlist_sql = """
        SHOW PROCESSLIST;
        """
        assert SQLParseHandler().parse_select_statement(show_processlist_sql) is None

        show_slave_sql = """
        SHOW SLAVE STATUS;
        """
        assert SQLParseHandler().parse_select_statement(show_slave_sql) is None

        show_create_table_sql = """
        SHOW CREATE TABLE TEST_DB.TEST_TABLE;
        """
        assert SQLParseHandler().parse_select_statement(show_create_table_sql) is None

        show_index_sql = """
        SHOW INDEX FROM TEST_DB.TEST_TABLE;
        """
        assert SQLParseHandler().parse_select_statement(show_index_sql) is None
