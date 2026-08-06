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
import zlib
from unittest.mock import MagicMock, patch

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql import explain_sql
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster import (
    ExplainSqlRouteContext,
    ShardKeyMatch,
    TableCreateInfo,
    _apply_shard_ids,
    _crc32_shard_id,
    _match_shard_key_values,
    _parse_partition_list_expr,
    _parse_route_context,
    _parse_shard_count_from_expr,
    _parse_shard_key_from_comment,
    _parse_shard_key_from_expr,
    _parse_spider_shard_meta,
    _rewrite_dbnames_for_shard,
    _rewrite_sql_for_shard,
    _route_shard_id,
)

USER_TABLE_CREATE_NO_COMMENT = """
CREATE TABLE `tb_test_1` (
  `id` int(11) NOT NULL,
  `val` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=SPIDER DEFAULT CHARSET=utf8
 PARTITION BY LIST (crc32(`id`) MOD 6)
(PARTITION `pt0` VALUES IN (0) COMMENT = 'database "dbtest_0"' ENGINE = SPIDER,
 PARTITION `pt1` VALUES IN (1) COMMENT = 'database "dbtest_1"' ENGINE = SPIDER,
 PARTITION `pt2` VALUES IN (2) COMMENT = 'database "dbtest_2"' ENGINE = SPIDER,
 PARTITION `pt3` VALUES IN (3) COMMENT = 'database "dbtest_3"' ENGINE = SPIDER,
 PARTITION `pt4` VALUES IN (4) COMMENT = 'database "dbtest_4"' ENGINE = SPIDER,
 PARTITION `pt5` VALUES IN (5) COMMENT = 'database "dbtest_5"' ENGINE = SPIDER)
"""

USER_TABLE_CREATE = """
CREATE TABLE `user` (
  `id` bigint NOT NULL,
  `name` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=SPIDER DEFAULT CHARSET=utf8mb4 COMMENT='shard_key "id"'
 PARTITION BY LIST (crc32(`id`) MOD 4)
(PARTITION `p0` VALUES IN (0) COMMENT = 'database "app_0"' ENGINE = INNODB,
 PARTITION `p1` VALUES IN (1) COMMENT = 'database "app_1"' ENGINE = INNODB,
 PARTITION `p2` VALUES IN (2) COMMENT = 'database "app_2"' ENGINE = INNODB,
 PARTITION `p3` VALUES IN (3) COMMENT = 'database "app_3"' ENGINE = INNODB)
"""


def _user_table_create(dbname: str = "app") -> TableCreateInfo:
    return TableCreateInfo(
        dbname=dbname,
        table_name="user",
        create_sql=USER_TABLE_CREATE,
        shard_key="id",
        shard_expr="crc32(`id`) MOD 4",
        shard_count=4,
    )


def _ctx_with_shard_match(
    *,
    sql: str,
    dbname: str,
    values: list,
    condition_key: str = "id",
) -> ExplainSqlRouteContext:
    ctx = _parse_route_context(sql, dbname)
    ctx.explained_sql = sql
    ctx.table_creates = [_user_table_create(dbname)]
    ctx.shard_key_matches = [
        ShardKeyMatch(
            dbname=dbname,
            table_name="user",
            shard_key="id",
            condition_key=condition_key,
            values=values,
        )
    ]
    _apply_shard_ids(ctx)
    return ctx


class TestParseSpiderShardMeta:
    def test_parse_shard_key_from_comment(self):
        assert _parse_shard_key_from_comment(USER_TABLE_CREATE) == "id"

    def test_parse_partition_list_expr(self):
        assert _parse_partition_list_expr(USER_TABLE_CREATE) == "crc32(`id`) MOD 4"

    def test_parse_shard_count_from_expr(self):
        assert _parse_shard_count_from_expr("crc32(`id`) MOD 4") == 4

    def test_parse_spider_shard_meta(self):
        shard_key, shard_expr, shard_count = _parse_spider_shard_meta(USER_TABLE_CREATE)
        assert shard_key == "id"
        assert shard_expr == "crc32(`id`) MOD 4"
        assert shard_count == 4

    def test_parse_shard_key_from_partition_expr_when_comment_missing(self):
        assert _parse_shard_key_from_comment(USER_TABLE_CREATE_NO_COMMENT) is None
        assert _parse_shard_key_from_expr("crc32(`id`) MOD 6") == "id"

        shard_key, shard_expr, shard_count = _parse_spider_shard_meta(USER_TABLE_CREATE_NO_COMMENT)
        assert shard_key == "id"
        assert shard_expr == "crc32(`id`) MOD 6"
        assert shard_count == 6

    def test_id_22_routes_to_shard_2_without_table_comment(self):
        ctx = _parse_route_context("SELECT * FROM dbtest.tb_test_1 WHERE id = 22", "dbtest")
        shard_key, shard_expr, shard_count = _parse_spider_shard_meta(USER_TABLE_CREATE_NO_COMMENT)
        ctx.table_creates = [
            TableCreateInfo(
                dbname="dbtest",
                table_name="tb_test_1",
                create_sql=USER_TABLE_CREATE_NO_COMMENT,
                shard_key=shard_key,
                shard_expr=shard_expr,
                shard_count=shard_count,
            )
        ]
        ctx.shard_key_matches = _match_shard_key_values(ctx)
        _apply_shard_ids(ctx)
        assert _route_shard_id(ctx) == (zlib.crc32(b"22") & 0xFFFFFFFF) % 6
        assert _route_shard_id(ctx) == 2


class TestCrc32ShardId:
    def test_crc32_shard_id(self):
        assert _crc32_shard_id("123", 4) == (zlib.crc32(b"123") & 0xFFFFFFFF) % 4
        assert _crc32_shard_id(None, 4) == (zlib.crc32(b"") & 0xFFFFFFFF) % 4


class TestParseRouteContext:
    def test_simple_where_eq(self):
        ctx = _parse_route_context("SELECT * FROM user WHERE id = 123", "app")
        assert len(ctx.tables) == 1
        assert ctx.tables[0].table_name == "user"
        assert ctx.tables[0].dbname == "app"
        assert ctx.where_eq["id"] == [123]

    def test_qualified_table_and_alias(self):
        sql = "SELECT * FROM app.user u WHERE u.id = 5"
        ctx = _parse_route_context(sql, "app")
        assert ctx.tables[0].alias == "u"
        assert ctx.where_eq["u.id"] == [5]

    def test_join_on_literal_and_table_eq(self):
        sql = "SELECT * FROM app.user u " "JOIN app.order o ON u.id = o.user_id " "WHERE o.status = 1"
        ctx = _parse_route_context(sql, "app")
        assert len(ctx.tables) == 2
        assert len(ctx.joins) == 1
        assert ctx.joins[0].on_table_eq == [("u.id", "o.user_id")]
        assert ctx.where_eq["o.status"] == [1]

    def test_in_list_values(self):
        ctx = _parse_route_context("SELECT * FROM user WHERE id IN (1, 2, 3)", "app")
        assert ctx.where_eq["id"] == [1, 2, 3]

    def test_subquery_table_extracted(self):
        sql = "SELECT * FROM user WHERE id IN (SELECT user_id FROM order_tbl WHERE status = 1)"
        ctx = _parse_route_context(sql, "app")
        physical = {(t.dbname, t.table_name) for t in ctx.physical_tables()}
        assert ("app", "user") in physical
        assert ("app", "order_tbl") in physical


class TestMatchShardKeyValues:
    def test_match_direct_where(self):
        ctx = _parse_route_context("SELECT * FROM user WHERE id = 123", "app")
        ctx.table_creates = [_user_table_create()]
        matches = _match_shard_key_values(ctx)
        assert len(matches) == 1
        assert matches[0].condition_key == "id"
        assert matches[0].values == [123]

    def test_match_via_join_propagation(self):
        sql = "SELECT * FROM app.user u " "JOIN app.profile p ON u.id = p.user_id " "WHERE p.user_id = 99"
        ctx = _parse_route_context(sql, "app")
        ctx.table_creates = [
            _user_table_create(),
            TableCreateInfo(
                dbname="app",
                table_name="profile",
                create_sql=USER_TABLE_CREATE.replace("`user`", "`profile`"),
                shard_key="user_id",
                shard_expr="crc32(`user_id`) MOD 4",
                shard_count=4,
            ),
        ]
        matches = _match_shard_key_values(ctx)
        user_match = next(m for m in matches if m.table_name == "user")
        assert user_match.condition_key == "p.user_id"
        assert user_match.values == [99]

    def test_no_match_defaults_empty_values(self):
        ctx = _parse_route_context("SELECT * FROM user WHERE name = 'alice'", "app")
        ctx.table_creates = [_user_table_create()]
        matches = _match_shard_key_values(ctx)
        assert matches[0].values == []


class TestShardRouting:
    def test_apply_shard_id_from_where(self):
        ctx = _ctx_with_shard_match(
            sql="SELECT * FROM user WHERE id = 123",
            dbname="app",
            values=[123],
        )
        expected = (zlib.crc32(b"123") & 0xFFFFFFFF) % 4
        assert ctx.shard_key_matches[0].shard_id == expected
        assert _route_shard_id(ctx) == expected

    def test_no_shard_value_defaults_to_zero(self):
        ctx = _ctx_with_shard_match(
            sql="SELECT * FROM user WHERE name = 'alice'",
            dbname="app",
            values=[],
            condition_key=None,
        )
        assert ctx.shard_key_matches[0].shard_id == 0
        assert _route_shard_id(ctx) == 0


class TestRewriteDbnamesForShard:
    def test_rewrite_table_and_column_db_prefix(self):
        sql = "SELECT app.user.id FROM app.user WHERE app.user.id = 1"
        out = _rewrite_dbnames_for_shard(sql, 2)
        assert "app_2.user" in out
        assert "app.user" not in out

    def test_skip_system_db(self):
        sql = "SELECT * FROM information_schema.tables WHERE table_schema = 'app'"
        out = _rewrite_dbnames_for_shard(sql, 2)
        assert "information_schema" in out
        assert "information_schema_2" not in out

    def test_no_db_prefix_unchanged(self):
        sql = "SELECT * FROM user WHERE id = 1"
        out = _rewrite_dbnames_for_shard(sql, 2)
        assert out == "SELECT * FROM user WHERE id = 1"


class TestRewriteSqlForShard:
    def test_step6_outputs(self):
        ctx = _ctx_with_shard_match(
            sql="SELECT * FROM app.user WHERE id = 123",
            dbname="app",
            values=[123],
        )
        _rewrite_sql_for_shard(ctx)
        shard_id = _route_shard_id(ctx)
        assert f"app_{shard_id}.user" in ctx.remote_explain_sql
        assert ctx.route_physical_dbname == f"app_{shard_id}"


class TestExplainSqlTendbclusterEndToEnd:
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.drs.DRSApi.v2_webconsole_rpc")
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster.TenDBClusterStorageSet")
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster._get_tendbcluster")
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster._fetch_spider_table_creates")
    def test_full_flow_with_shard_key(
        self,
        mock_fetch_creates,
        mock_get_cluster,
        mock_storage_set_cls,
        mock_drs_rpc,
    ):
        mock_fetch_creates.return_value = [_user_table_create("app")]

        cluster_obj = MagicMock()
        cluster_obj.bk_cloud_id = 0
        cluster_obj.immute_domain = "spider.example.db"
        mock_get_cluster.return_value = cluster_obj

        receiver = MagicMock()
        receiver.ip_port = "127.0.0.1:3306"
        storage_set = MagicMock()
        storage_set.storage_instance_tuple.receiver = receiver
        mock_storage_set_cls.objects.get.return_value = storage_set

        explain_rows = [{"id": 1, "select_type": "SIMPLE", "table": "user"}]
        mock_drs_rpc.return_value = [
            {
                "error_msg": "",
                "cmd_results": [
                    {"error_msg": "", "table_data": []},
                    {"error_msg": "", "table_data": explain_rows},
                ],
            }
        ]

        result = explain_sql(
            cluster_type=ClusterType.TenDBCluster,
            cluster_domain="spider.example.db",
            dbname="app",
            query_sql="SELECT * FROM user WHERE id = 123",
        )

        shard_id = (zlib.crc32(b"123") & 0xFFFFFFFF) % 4
        assert result["explain_result"] == explain_rows
        assert result["rewritten"] is False

        mock_storage_set_cls.objects.get.assert_called_once_with(cluster=cluster_obj, shard_id=shard_id)
        drs_payload = mock_drs_rpc.call_args[0][0]
        assert drs_payload["addresses"] == ["127.0.0.1:3306"]
        assert drs_payload["cmds"][0] == f"USE `app_{shard_id}`"
        assert drs_payload["cmds"][1].startswith("EXPLAIN ")

    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.drs.DRSApi.v2_webconsole_rpc")
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster.TenDBClusterStorageSet")
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster._get_tendbcluster")
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster._fetch_spider_table_creates")
    def test_full_flow_without_shard_key_defaults_shard_zero(
        self,
        mock_fetch_creates,
        mock_get_cluster,
        mock_storage_set_cls,
        mock_drs_rpc,
    ):
        mock_fetch_creates.return_value = [_user_table_create("app")]

        cluster_obj = MagicMock()
        cluster_obj.bk_cloud_id = 0
        cluster_obj.immute_domain = "spider.example.db"
        mock_get_cluster.return_value = cluster_obj

        receiver = MagicMock()
        receiver.ip_port = "127.0.0.1:3306"
        storage_set = MagicMock()
        storage_set.storage_instance_tuple.receiver = receiver
        mock_storage_set_cls.objects.get.return_value = storage_set

        mock_drs_rpc.return_value = [
            {
                "error_msg": "",
                "cmd_results": [
                    {"error_msg": "", "table_data": []},
                    {"error_msg": "", "table_data": [{"id": 1}]},
                ],
            }
        ]

        result = explain_sql(
            cluster_type=ClusterType.TenDBCluster,
            cluster_domain="spider.example.db",
            dbname="app",
            query_sql="SELECT * FROM user WHERE name = 'alice'",
        )

        assert result["explain_result"] == [{"id": 1}]
        assert result["rewritten"] is False
        mock_storage_set_cls.objects.get.assert_called_once_with(cluster=cluster_obj, shard_id=0)
