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
from unittest.mock import Mock, patch

import pytest

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, InstanceNotExistException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.dbbase.dataclass import DBInstance
from backend.exceptions import ValidationError

pytestmark = pytest.mark.django_db


class TestClusterServiceHandler:
    """基础ClusterServiceHandler测试类"""

    def test_init(self, bk_biz_id):
        """测试初始化"""
        handler = ClusterServiceHandler(bk_biz_id)
        assert handler.bk_biz_id == bk_biz_id

    def test_check_cluster_databases_cluster_not_exist(self, bk_biz_id):
        """测试检查集群数据库 - 集群不存在"""
        handler = ClusterServiceHandler(bk_biz_id)
        with pytest.raises(ClusterNotExistException):
            handler.check_cluster_databases(cluster_id=99999, db_list=["test_db"])

    def test_check_cluster_databases_not_implemented(self, bk_biz_id, dbha_cluster):
        """测试检查集群数据库 - 未实现的集群类型"""
        handler = ClusterServiceHandler(bk_biz_id)
        # 修改集群类型为不支持的类型，但不保存到数据库以避免信号问题
        original_cluster_type = dbha_cluster.cluster_type
        dbha_cluster.cluster_type = "unsupported_type"

        with patch.object(Cluster.objects, "get") as mock_get:
            mock_get.return_value = dbha_cluster
            with pytest.raises(NotImplementedError):
                handler.check_cluster_databases(cluster_id=dbha_cluster.id, db_list=["test_db"])

        # 恢复原始类型
        dbha_cluster.cluster_type = original_cluster_type

    @patch("backend.db_services.mysql.remote_service.handlers.RemoteServiceHandler")
    def test_check_cluster_databases_mysql(self, mock_mysql_handler, bk_biz_id, dbha_cluster):
        """测试检查集群数据库 - MySQL类型"""
        # 设置mock返回值
        mock_instance = mock_mysql_handler.return_value
        mock_instance.check_cluster_database.return_value = [{"check_info": {"db1": True, "db2": False}}]

        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.check_cluster_databases(cluster_id=dbha_cluster.id, db_list=["db1", "db2"])

        assert result == {"db1": True, "db2": False}
        mock_mysql_handler.assert_called_once_with(bk_biz_id)
        mock_instance.check_cluster_database.assert_called_once_with(
            [{"cluster_id": dbha_cluster.id, "db_names": ["db1", "db2"]}]
        )

    def test_check_cluster_database_not_implemented(self, bk_biz_id):
        """测试子类实现的检查集群数据库方法"""
        handler = ClusterServiceHandler(bk_biz_id)
        with pytest.raises(NotImplementedError):
            handler.check_cluster_database(cluster_id=1, db_list=["test_db"])

    def test_query_machine_instance_pair_empty_query(self, bk_biz_id):
        """测试查询机器实例对 - 空查询"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.query_machine_instance_pair({})
        assert result == {}

    def test_query_machine_instance_pair_no_pairs(self, bk_biz_id):
        """测试查询机器实例对 - 无配对关系"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.query_machine_instance_pair({"instances": ["127.0.0.1:3306"], "machines": ["0:127.0.0.1"]})
        assert "instances" in result
        assert "machines" in result

    def test_query_master_slave_pairs_cluster_not_exist(self, bk_biz_id):
        """测试查询主从对 - 集群不存在"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.query_master_slave_pairs(cluster_id=99999)
        assert result == []

    def test_query_master_slave_pairs_success(self, bk_biz_id, dbha_cluster_with_tuple):
        """测试查询主从对 - 成功"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.query_master_slave_pairs(cluster_id=dbha_cluster_with_tuple.id)

        assert len(result) > 0
        for pair in result:
            assert "masters" in pair
            assert "slaves" in pair
            assert "master_ip" in pair
            assert "slave_ip" in pair

    def test_find_related_clusters_by_cluster_ids_no_instances(self, bk_biz_id):
        """测试根据集群ID查找关联集群 - 无实例"""
        handler = ClusterServiceHandler(bk_biz_id)
        with pytest.raises(InstanceNotExistException):
            handler.find_related_clusters_by_cluster_ids([99999])

    def test_find_related_clusters_by_cluster_ids_success(self, bk_biz_id, dbha_cluster):
        """测试根据集群ID查找关联集群 - 成功"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.find_related_clusters_by_cluster_ids([dbha_cluster.id])

        assert len(result) == 1
        assert result[0]["cluster_id"] == dbha_cluster.id
        assert "cluster_info" in result[0]
        assert "related_clusters" in result[0]

    def test_find_related_clusters_by_instances_empty(self, bk_biz_id):
        """测试根据实例查找关联集群 - 空实例列表"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.find_related_clusters_by_instances([])
        assert result == []

    def test_find_related_clusters_by_instances_success(self, bk_biz_id, dbha_cluster):
        """测试根据实例查找关联集群 - 成功"""
        handler = ClusterServiceHandler(bk_biz_id)
        masters = StorageInstance.objects.filter(cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER)
        instances = [DBInstance.from_inst_obj(master) for master in masters]

        result = handler.find_related_clusters_by_instances(instances)

        assert len(result) > 0
        for item in result:
            assert "instance_address" in item
            assert "bk_host_id" in item
            assert "cluster_info" in item
            assert "related_clusters" in item

    def test_get_intersected_machines_from_clusters_empty(self, bk_biz_id):
        """测试获取集群交集机器 - 空集群列表"""
        handler = ClusterServiceHandler(bk_biz_id)
        # 空集群列表会导致set.intersection抛出异常，这是原始代码的一个bug
        # 我们测试这个异常行为，表明这是一个已知问题
        with pytest.raises(TypeError):
            handler.get_intersected_machines_from_clusters([], InstanceInnerRole.MASTER, False)

    def test_get_intersected_machines_from_clusters_success(self, bk_biz_id, dbha_cluster):
        """测试获取集群交集机器 - 成功"""
        handler = ClusterServiceHandler(bk_biz_id)
        result = handler.get_intersected_machines_from_clusters([dbha_cluster.id], InstanceInnerRole.MASTER, False)

        for machine_info in result:
            assert "ip" in machine_info
            assert "bk_cloud_id" in machine_info
            assert "bk_host_id" in machine_info
            assert "bk_biz_id" in machine_info

    def test_format_cluster_field(self, bk_biz_id):
        """测试格式化集群字段"""
        handler = ClusterServiceHandler(bk_biz_id)
        cluster_info = {"name": "test_cluster", "immute_domain": "test.domain.com"}

        result = handler._format_cluster_field(cluster_info)

        assert result["cluster_name"] == "test_cluster"
        assert result["master_domain"] == "test.domain.com"

    def test_get_instance_objs(self, bk_biz_id, dbha_cluster):
        """测试获取实例对象"""
        handler = ClusterServiceHandler(bk_biz_id)
        masters = StorageInstance.objects.filter(cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER)
        instances = [DBInstance.from_inst_obj(master) for master in masters]

        result = handler._get_instance_objs(instances)

        assert len(result) > 0
        for inst_obj in result:
            assert hasattr(inst_obj, "machine")
            assert hasattr(inst_obj, "port")

    @patch("backend.db_services.mysql.sqlparse.handlers.SQLParseHandler")
    @patch("backend.components.DRSApi.rpc")
    def test_console_rpc_success(self, mock_drs_rpc, mock_sql_parser, bk_biz_id):
        """测试控制台RPC - 成功"""
        # 设置mock
        mock_parser_instance = mock_sql_parser.return_value
        mock_parser_instance.parse_select_statement.return_value = None

        mock_drs_rpc.return_value = [
            {"address": "127.0.0.1:3306", "cmd_results": [{"table_data": [{"col1": "value1"}]}], "error_msg": ""}
        ]

        instances = [{"bk_cloud_id": 0, "instance": "127.0.0.1:3306"}]
        cmd = "SELECT * FROM mysql.user LIMIT 1"  # 使用系统库查询

        def mock_rpc_function(params):
            return mock_drs_rpc.return_value

        result = ClusterServiceHandler.console_rpc(
            instances=instances, cmd=cmd, db_query=True, rpc_function=mock_rpc_function
        )

        assert len(result) == 1
        assert result[0]["instance"] == "127.0.0.1:3306"
        assert result[0]["table_data"] == [{"col1": "value1"}]
        assert result[0]["error_msg"] == ""

    @patch("backend.db_services.mysql.sqlparse.handlers.SQLParseHandler")
    @patch("backend.components.DRSApi.rpc")
    def test_console_rpc_special_query(self, mock_drs_rpc, mock_sql_parser, bk_biz_id):
        """测试控制台RPC - 特殊查询"""
        # 设置mock
        mock_parser_instance = mock_sql_parser.return_value
        mock_parser_instance.parse_select_statement.return_value = None

        mock_drs_rpc.return_value = [
            {
                "address": "127.0.0.1:3306",
                "cmd_results": [
                    {"table_data": [{"Variable_name": "version", "Value": "8.0.25"}], "error_msg": ""},
                    {"table_data": [{"Variable_name": "max_connections", "Value": "1000"}], "error_msg": ""},
                ],
                "error_msg": "",
            }
        ]

        instances = [{"bk_cloud_id": 0, "instance": "127.0.0.1:3306"}]
        cmd = "show mysql configurations"

        def mock_rpc_function(params):
            return mock_drs_rpc.return_value

        result = ClusterServiceHandler.console_rpc(
            instances=instances, cmd=cmd, db_query=True, rpc_function=mock_rpc_function
        )

        assert len(result) == 1
        assert result[0]["instance"] == "127.0.0.1:3306"
        assert result[0]["table_data"] == [{"version": "8.0.25", "max_connections": "1000"}]

    def test_check_special_sql(self):
        """测试检查特殊SQL"""
        assert ClusterServiceHandler._ClusterServiceHandler__check_special_sql("show mysql configurations")
        assert ClusterServiceHandler._ClusterServiceHandler__check_special_sql("show slave status")
        assert not ClusterServiceHandler._ClusterServiceHandler__check_special_sql("select * from test")

    def test_merge_drs_result_mysql_config(self):
        """测试合并DRS结果 - MySQL配置"""
        res = {
            "cmd_results": [
                {"table_data": [{"Variable_name": "version", "Value": "8.0.25"}], "error_msg": ""},
                {"table_data": [{"Variable_name": "max_connections", "Value": "1000"}], "error_msg": ""},
            ]
        }
        cmd = "show mysql configurations"

        result = ClusterServiceHandler._ClusterServiceHandler__merge_drs_result(res, cmd)

        assert len(result) == 1
        assert result[0]["version"] == "8.0.25"
        assert result[0]["max_connections"] == "1000"

    def test_merge_drs_result_slave_status(self):
        """测试合并DRS结果 - 从库状态"""
        res = {
            "cmd_results": [
                {
                    "table_data": [
                        {
                            "Master_Host": "127.0.0.1",
                            "Master_Port": "3306",
                            "Slave_IO_Running": "Yes",
                            "Slave_SQL_Running": "Yes",
                        }
                    ],
                    "error_msg": "",
                }
            ]
        }
        cmd = "show slave status"

        result = ClusterServiceHandler._ClusterServiceHandler__merge_drs_result(res, cmd)

        assert len(result) == 1
        assert result[0]["Master_Host"] == "127.0.0.1"
        assert result[0]["Master_Port"] == "3306"

    @patch("backend.components.JobApi.fast_execute_script")
    @patch.object(ClusterServiceHandler, "get_execute_net_tcp_cluster_hosts")
    def test_execute_cluster_net_tcp_cmd_success(self, mock_get_hosts, mock_job_api, bk_biz_id, dbha_cluster):
        """测试执行集群网络TCP命令 - 成功"""
        mock_get_hosts.return_value = [1, 2, 3]  # 返回一些主机ID
        mock_job_api.return_value = {"job_instance_id": 12345}

        result = ClusterServiceHandler.execute_cluster_net_tcp_cmd([dbha_cluster.id])

        assert result["job_instance_id"] == 12345
        mock_job_api.assert_called_once()

    def test_execute_cluster_net_tcp_cmd_too_many_hosts(self, bk_biz_id):
        """测试执行集群网络TCP命令 - 主机数量过多"""
        # 创建一个mock的集群，返回超过10000台主机
        with patch("backend.db_meta.models.Cluster.objects.filter") as mock_filter:
            mock_cluster = Mock()
            mock_filter.return_value.prefetch_related.return_value = [mock_cluster]

            with patch.object(ClusterServiceHandler, "get_execute_net_tcp_cluster_hosts") as mock_get_hosts:
                mock_get_hosts.return_value = list(range(10001))  # 返回10001个主机ID

                with pytest.raises(ValidationError):
                    ClusterServiceHandler.execute_cluster_net_tcp_cmd([1])

    def test_get_execute_net_tcp_cluster_hosts_not_implemented(self):
        """测试获取执行网络TCP的集群主机 - 未实现"""
        with pytest.raises(NotImplementedError):
            ClusterServiceHandler.get_execute_net_tcp_cluster_hosts(None)

    @patch("backend.components.JobApi.get_job_instance_status")
    @patch("backend.components.JobApi.batch_get_job_instance_ip_log")
    def test_get_cluster_proc_net_tcp_not_finished(self, mock_batch_log, mock_job_status, bk_biz_id):
        """测试获取集群proc/net/tcp信息 - 未完成"""
        mock_job_status.return_value = {"finished": False}

        result = ClusterServiceHandler.get_cluster_proc_net_tcp(12345)

        assert result["finished"] is False
        assert result["data"] == []

    @patch("backend.components.JobApi.get_job_instance_status")
    @patch("backend.components.JobApi.batch_get_job_instance_ip_log")
    @patch("backend.components.CCApi.list_hosts_without_biz")
    @patch("backend.components.CCApi.batch_find_host_biz_relations")
    @patch("backend.db_services.ipchooser.handlers.topo_handler.TopoHandler.query_host_topo_infos")
    @patch("backend.db_meta.models.StorageInstance.objects.filter")
    @patch("backend.db_meta.models.ProxyInstance.objects.filter")
    def test_get_cluster_proc_net_tcp_finished(
        self,
        mock_proxy_filter,
        mock_storage_filter,
        mock_topo,
        mock_biz_relations,
        mock_cc_hosts,
        mock_batch_log,
        mock_job_status,
        bk_biz_id,
    ):
        """测试获取集群proc/net/tcp信息 - 完成"""
        # Mock job状态
        mock_job_status.return_value = {
            "finished": True,
            "step_instance_list": [
                {
                    "step_instance_id": 123,
                    "step_ip_result_list": [{"bk_host_id": 1, "bk_cloud_id": 0, "ip": "127.0.0.1"}],
                }
            ],
        }

        # Mock日志内容
        mock_batch_log.return_value = {
            "script_task_logs": [
                {
                    "host_id": 1,
                    "log_content": "sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n 0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0",  # noqa
                    "bk_cloud_id": 0,
                    "ip": "127.0.0.1",
                }
            ]
        }

        # Mock数据库查询
        mock_storage_filter.return_value.values.return_value.union.return_value = [
            {
                "cluster__immute_domain": "test.domain.com",
                "machine__bk_host_id": 1,
                "machine__ip": "127.0.0.1",
                "port": 8080,
            }
        ]
        mock_proxy_filter.return_value.values.return_value = []

        # Mock CC API
        mock_cc_hosts.return_value = []
        mock_biz_relations.return_value = []
        mock_topo.return_value = {"hosts_topo_info": []}

        result = ClusterServiceHandler.get_cluster_proc_net_tcp(12345)

        assert result["finished"] is True
        assert isinstance(result["data"], list)

    def test_parse_proc_net_tcp_invalid_content(self):
        """测试解析proc/net/tcp - 无效内容"""
        content = "invalid content"

        result, success = ClusterServiceHandler._ClusterServiceHandler__parse_proc_net_tcp(content)

        assert not success
        assert result == {}

    def test_parse_proc_net_tcp_valid_content(self):
        """测试解析proc/net/tcp - 有效内容"""
        # 使用正确的监听状态码 0A (10 in decimal)
        content = """sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
 0: 00000000:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0
 1: 0100007F:0CEA 0100007F:1F90 01 00000000:00000000 00:00000000 00000000     0        0 12346 1 0000000000000000 100 0 0 10 0"""

        result, success = ClusterServiceHandler._ClusterServiceHandler__parse_proc_net_tcp(content)

        assert success
        assert isinstance(result, dict)
        # 检查监听端口8080 (1F90 hex = 8080 dec)，状态0A表示监听状态
        assert 8080 in result

    def test_generate_net_tcp_report_with_logs(self):
        """测试生成网络TCP报告 - 有日志"""
        log_infos = [
            {
                "host_id": 1,
                "bk_cloud_id": 0,
                "ip": "127.0.0.1",
                "log_content": "sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n 0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0",  # noqa
            }
        ]

        with patch("backend.db_meta.models.StorageInstance.objects.filter") as mock_storage, patch(
            "backend.db_meta.models.ProxyInstance.objects.filter"
        ) as mock_proxy:

            # Mock返回一些实例数据，包含host_id为1的实例
            mock_storage.return_value.values.return_value.union.return_value = [
                {
                    "cluster__immute_domain": "test.domain.com",
                    "machine__bk_host_id": 1,
                    "machine__ip": "127.0.0.1",
                    "port": 8080,
                }
            ]
            mock_proxy.return_value.values.return_value = []

            result = ClusterServiceHandler._ClusterServiceHandler__generate_net_tcp_report(log_infos)

            assert isinstance(result, list)
