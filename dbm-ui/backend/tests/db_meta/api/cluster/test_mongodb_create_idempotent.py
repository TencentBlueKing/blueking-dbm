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
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.api.cluster.mongocluster import create as mongocluster_create
from backend.db_meta.api.cluster.mongorepset import create as mongorepset_create
from backend.db_meta.enums import ClusterPhase, InstanceRole


def _atomic_noop():
    class _Ctx:
        def __enter__(self):
            return None

        def __exit__(self, *args):
            return False

    return _Ctx()


class TestCreateMongoClusterIdempotent:
    @patch("backend.db_meta.api.cluster.mongocluster.create.transaction.atomic", side_effect=_atomic_noop)
    @patch("backend.db_meta.api.cluster.mongocluster.create.apply_mongodb_metadata_versions_to_cluster")
    @patch("backend.db_meta.api.cluster.mongocluster.create.MongoDBCCTopoOperator")
    @patch("backend.db_meta.api.cluster.mongocluster.create._ensure_dns_entry")
    @patch("backend.db_meta.api.cluster.mongocluster.create._ensure_shard_rules")
    @patch("backend.db_meta.api.cluster.mongocluster.create._bind_cluster_instances")
    @patch("backend.db_meta.api.cluster.mongocluster.create.get_storage_objs")
    @patch("backend.db_meta.api.cluster.mongocluster.create.get_proxy_objs")
    @patch("backend.db_meta.api.cluster.mongocluster.create.find_reusable_cluster")
    def test_reuses_offline_cluster_and_sets_online(
        self,
        mock_find,
        mock_get_proxy,
        mock_get_storage,
        mock_bind,
        mock_rules,
        mock_dns,
        mock_cc,
        mock_version,
        mock_atomic,
    ):
        logs = []
        cluster = MagicMock()
        cluster.id = 7
        cluster.phase = ClusterPhase.OFFLINE.value
        mock_find.return_value = cluster
        mock_get_proxy.return_value = [MagicMock()]
        mock_get_storage.side_effect = [[MagicMock()], [MagicMock()]]  # storages, configs

        proxies = [{"ip": "127.0.0.1", "port": 27017}]
        configs = [
            {
                "shard": "config",
                "nodes": [{"ip": "127.0.0.2", "port": 27018, "role": InstanceRole.MONGO_M1}],
            }
        ]
        storages = [
            {
                "shard": "shard-0",
                "nodes": [{"ip": "127.0.0.3", "port": 27019, "role": InstanceRole.MONGO_M1}],
            }
        ]

        result = mongocluster_create.create_mongo_cluster(
            bk_biz_id=1,
            name="sc1",
            immute_domain="sc1.db",
            db_module_id=0,
            proxies=proxies,
            configs=configs,
            storages=storages,
            creator="admin",
            major_version="mongodb-6.0.5",
            progress_callback=logs.append,
        )
        assert result is cluster
        assert cluster.phase == ClusterPhase.ONLINE.value
        cluster.save.assert_called()
        mock_cc.return_value.transfer_instances_to_cluster_module.assert_called()
        assert any("reuse existing cluster" in msg for msg in logs)
        assert any("phase set to online" in msg for msg in logs)
        assert any("[start] create cluster relations" in msg for msg in logs)
        assert any("[start] sync CMDB" in msg for msg in logs)

    @patch("backend.db_meta.api.cluster.mongocluster.create.transaction.atomic", side_effect=_atomic_noop)
    @patch("backend.db_meta.api.cluster.mongocluster.create.create_proxies")
    @patch("backend.db_meta.api.cluster.mongocluster.create._create_missing_shard_instances")
    @patch("backend.db_meta.api.cluster.mongocluster.create.create_mongo_cluster")
    @patch("backend.db_meta.api.cluster.mongocluster.create.find_reusable_cluster", return_value=None)
    @patch("backend.db_meta.api.cluster.mongocluster.create.ClusterEntry.objects.filter")
    @patch("backend.db_meta.api.cluster.mongocluster.create.partition_proxy_inputs")
    def test_pkg_skips_existing_proxies(
        self,
        mock_partition_proxy,
        mock_entry_filter,
        mock_find,
        mock_create_cluster,
        mock_create_shards,
        mock_create_proxies,
        mock_atomic,
    ):
        logs = []
        reusable = [MagicMock()]
        mock_partition_proxy.return_value = ([], reusable, [])
        mock_entry_filter.return_value.first.return_value = None

        mongocluster_create.pkg_create_mongo_cluster(
            bk_biz_id=1,
            name="sc1",
            immute_domain="sc1.db",
            db_module_id=0,
            proxies=[{"ip": "127.0.0.1", "port": 27017}],
            configs=[
                {"shard": "config", "nodes": [{"ip": "127.0.0.2", "port": 27018, "role": InstanceRole.MONGO_M1}]}
            ],
            storages=[{"shard": "s0", "nodes": [{"ip": "127.0.0.3", "port": 27019, "role": InstanceRole.MONGO_M1}]}],
            creator="admin",
            progress_callback=logs.append,
        )
        mock_create_proxies.assert_not_called()
        assert mock_create_shards.call_count == 2
        mock_create_cluster.assert_called_once()
        assert any("skipped=1" in msg for msg in logs)


class TestCreateMongosetIdempotent:
    @patch("backend.db_meta.api.cluster.mongorepset.create.transaction.atomic", side_effect=_atomic_noop)
    @patch("backend.db_meta.api.cluster.mongorepset.create.apply_mongodb_metadata_versions_to_cluster")
    @patch("backend.db_meta.api.cluster.mongorepset.create.MongoDBCCTopoOperator")
    @patch("backend.db_meta.api.cluster.mongorepset.create._ensure_replicaset_dns_entries")
    @patch("backend.db_meta.api.cluster.mongorepset.create.update_cluster_type")
    @patch("backend.db_meta.api.cluster.mongorepset.create.get_storage_objs")
    @patch("backend.db_meta.api.cluster.mongorepset.create.find_reusable_cluster")
    def test_reuses_offline_and_sets_online(
        self,
        mock_find,
        mock_get_storage,
        mock_update_type,
        mock_dns,
        mock_cc,
        mock_version,
        mock_atomic,
    ):
        logs = []
        cluster = MagicMock()
        cluster.id = 3
        cluster.phase = ClusterPhase.OFFLINE.value
        cluster.storageinstance_set = MagicMock()
        mock_find.return_value = cluster
        mock_get_storage.return_value = [MagicMock()]

        storages = [
            {"ip": "127.0.0.1", "port": 27001, "role": InstanceRole.MONGO_M1, "domain": "rs1.db"},
        ]
        result = mongorepset_create.create_mongoset(
            bk_biz_id=1,
            name="rs1",
            immute_domain="rs1.db",
            db_module_id=0,
            storages=storages,
            creator="admin",
            major_version="mongodb-6.0.5",
            progress_callback=logs.append,
        )
        assert result is cluster
        assert cluster.phase == ClusterPhase.ONLINE.value
        mock_cc.return_value.transfer_replicaset_deploy_instances_to_cluster_module.assert_called_once()
        assert any("phase set to online" in msg for msg in logs)

    @patch("backend.db_meta.api.cluster.mongorepset.create.transaction.atomic", side_effect=_atomic_noop)
    @patch(
        "backend.db_meta.api.cluster.mongorepset.create.partition_storage_inputs",
        return_value=([], [], ["127.0.0.1:27001 already belongs to another cluster"]),
    )
    @patch("backend.db_meta.api.cluster.mongorepset.create.find_reusable_cluster", return_value=None)
    def test_conflict_other_cluster_instance_fails(self, mock_find, mock_partition, mock_atomic):
        with pytest.raises(Exception, match="already belongs"):
            mongorepset_create.pkg_create_mongoset(
                bk_biz_id=1,
                name="rs1",
                immute_domain="rs1.db",
                db_module_id=0,
                storages=[
                    {"ip": "127.0.0.1", "port": 27001, "role": InstanceRole.MONGO_M1, "domain": "rs1.db"},
                ],
                creator="admin",
            )
