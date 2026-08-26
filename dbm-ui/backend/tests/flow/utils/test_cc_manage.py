# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import ClusterMonitorTopo
from backend.exceptions import ApiError
from backend.flow.consts import OperateCollectorActionEnum
from backend.flow.utils.cc_manage import CcManage, operate_bklog_host_collectors


def _build_cc_manage():
    return CcManage(bk_biz_id=3, cluster_type=ClusterType.MongoReplicaSet.value)


def _mock_topo_objects(bk_module_id=4238, bk_set_id=96):
    topo_obj = SimpleNamespace(
        bk_biz_id=3,
        bk_set_id=bk_set_id,
        bk_module_id=bk_module_id,
        delete=MagicMock(),
    )
    app_topo = SimpleNamespace(bk_set_id=bk_set_id)
    return topo_obj, app_topo


@patch("backend.flow.utils.cc_manage.BizSettings.get_exact_hosting_biz", return_value=3)
@patch("backend.flow.utils.cc_manage.CCApi.delete_module")
@patch("backend.flow.utils.cc_manage.CCApi.transfer_host_module")
@patch("backend.flow.utils.cc_manage.CCApi.find_module_host_relation")
@patch("backend.flow.utils.cc_manage.CCApi.search_module")
@patch("backend.flow.utils.cc_manage.CCApi.list_biz_hosts")
@patch("backend.flow.utils.cc_manage.ClusterMonitorTopo.objects.get")
@patch("backend.flow.utils.cc_manage.AppMonitorTopo.objects.get")
def test_delete_cc_module_detaches_shared_hosts_before_delete(
    mock_app_topo_get,
    mock_topo_get,
    mock_list_biz_hosts,
    mock_search_module,
    mock_find_module_host_relation,
    mock_transfer_host_module,
    mock_delete_module,
    _mock_hosting_biz,
):
    cc_manage = _build_cc_manage()
    topo_obj, app_topo = _mock_topo_objects()
    mock_topo_get.return_value = topo_obj
    mock_app_topo_get.return_value = app_topo
    mock_list_biz_hosts.return_value = {"info": [{"bk_host_id": 101}, {"bk_host_id": 102}]}
    mock_search_module.return_value = {"info": [{"bk_module_id": 4238}, {"bk_module_id": 4239}]}
    mock_find_module_host_relation.return_value = {
        "relation": [
            {"host": {"bk_host_id": 101}, "modules": [{"bk_module_id": 4238}, {"bk_module_id": 4239}]},
            {"host": {"bk_host_id": 102}, "modules": [{"bk_module_id": 4238}, {"bk_module_id": 4239}]},
        ]
    }

    cc_manage.delete_cc_module("mongodb", ClusterType.MongoReplicaSet.value, cluster_id=63)

    assert mock_transfer_host_module.call_count == 2
    for call in mock_transfer_host_module.call_args_list:
        assert call.args[0]["bk_module_id"] == [4239]
        assert call.args[0]["is_increment"] is False
    mock_delete_module.assert_called_once_with(
        {"bk_biz_id": 3, "bk_set_id": 96, "bk_module_id": 4238},
    )
    topo_obj.delete.assert_called_once_with(keep_parents=True)


@patch("backend.flow.utils.cc_manage.BizSettings.get_exact_hosting_biz", return_value=3)
@patch("backend.flow.utils.cc_manage.CcManage.recycle_host")
@patch("backend.flow.utils.cc_manage.CCApi.delete_module")
@patch("backend.flow.utils.cc_manage.CCApi.find_module_host_relation")
@patch("backend.flow.utils.cc_manage.CCApi.search_module")
@patch("backend.flow.utils.cc_manage.CCApi.list_biz_hosts")
@patch("backend.flow.utils.cc_manage.ClusterMonitorTopo.objects.get")
@patch("backend.flow.utils.cc_manage.AppMonitorTopo.objects.get")
def test_delete_cc_module_recycles_exclusive_hosts(
    mock_app_topo_get,
    mock_topo_get,
    mock_list_biz_hosts,
    mock_search_module,
    mock_find_module_host_relation,
    mock_delete_module,
    mock_recycle_host,
    _mock_hosting_biz,
):
    cc_manage = _build_cc_manage()
    topo_obj, app_topo = _mock_topo_objects(bk_module_id=5001)
    mock_topo_get.return_value = topo_obj
    mock_app_topo_get.return_value = app_topo
    mock_list_biz_hosts.return_value = {"info": [{"bk_host_id": 201}]}
    mock_search_module.return_value = {"info": [{"bk_module_id": 5001}]}
    mock_find_module_host_relation.return_value = {
        "relation": [{"host": {"bk_host_id": 201}, "modules": [{"bk_module_id": 5001}]}]
    }

    cc_manage.delete_cc_module("mongodb", ClusterType.MongoReplicaSet.value, cluster_id=70)

    mock_recycle_host.assert_called_once_with([201])
    mock_delete_module.assert_called_once()


@patch("backend.flow.utils.cc_manage.BizSettings.get_exact_hosting_biz", return_value=3)
@patch("backend.flow.utils.cc_manage.CCApi.delete_module")
@patch("backend.flow.utils.cc_manage.CCApi.list_biz_hosts")
@patch("backend.flow.utils.cc_manage.ClusterMonitorTopo.objects.get")
@patch("backend.flow.utils.cc_manage.AppMonitorTopo.objects.get")
def test_delete_cc_module_deletes_empty_module_directly(
    mock_app_topo_get,
    mock_topo_get,
    mock_list_biz_hosts,
    mock_delete_module,
    _mock_hosting_biz,
):
    cc_manage = _build_cc_manage()
    topo_obj, app_topo = _mock_topo_objects()
    mock_topo_get.return_value = topo_obj
    mock_app_topo_get.return_value = app_topo
    mock_list_biz_hosts.return_value = {"info": []}

    cc_manage.delete_cc_module("mongodb", ClusterType.MongoReplicaSet.value, cluster_id=63)

    mock_delete_module.assert_called_once()
    topo_obj.delete.assert_called_once_with(keep_parents=True)


@patch("backend.flow.utils.cc_manage.BizSettings.get_exact_hosting_biz", return_value=3)
@patch("backend.flow.utils.cc_manage.CCApi.delete_module")
@patch("backend.flow.utils.cc_manage.ClusterMonitorTopo.objects.get")
@patch("backend.flow.utils.cc_manage.AppMonitorTopo.objects.get")
def test_delete_cc_module_skips_when_topo_missing(
    mock_app_topo_get,
    mock_topo_get,
    mock_delete_module,
    _mock_hosting_biz,
):
    cc_manage = _build_cc_manage()
    _, app_topo = _mock_topo_objects()
    mock_app_topo_get.return_value = app_topo
    mock_topo_get.side_effect = ClusterMonitorTopo.DoesNotExist

    cc_manage.delete_cc_module("mongodb", ClusterType.MongoReplicaSet.value, cluster_id=63)

    mock_delete_module.assert_not_called()


@patch("backend.flow.utils.cc_manage.env")
@patch("backend.flow.utils.cc_manage.BKLogApi")
def test_operate_bklog_host_collectors_runs_host_scope(mock_bklog_api, mock_env):
    mock_env.DBA_APP_BK_BIZ_ID = 3
    mock_bklog_api.list_collectors.return_value = {
        "list": [
            {"collector_config_name_en": "backup_stm_log", "collector_config_id": 11},
            {"collector_config_name_en": "dbm_retry_event", "collector_config_id": 12},
        ]
    }

    operate_bklog_host_collectors(
        bk_host_ids=[101, 102],
        action=OperateCollectorActionEnum.UNINSTALL.value,
        collector_names=["backup_stm_log", "dbm_retry_event"],
        bk_biz_id=9,
    )

    assert mock_bklog_api.run_databus_collectors.call_count == 2
    first_call = mock_bklog_api.run_databus_collectors.call_args_list[0]
    params = first_call.kwargs.get("params") or first_call.args[0]
    assert params["bk_biz_id"] == 3
    assert params["action"] == OperateCollectorActionEnum.UNINSTALL.value
    assert params["scope"]["object_type"] == "HOST"
    assert params["scope"]["bk_biz_id"] == 9
    assert {node["bk_host_id"] for node in params["scope"]["nodes"]} == {101, 102}


@patch("backend.flow.utils.cc_manage.env")
@patch("backend.flow.utils.cc_manage.BKLogApi")
def test_operate_bklog_host_collectors_skips_missing_and_api_error(mock_bklog_api, mock_env):
    mock_env.DBA_APP_BK_BIZ_ID = 3
    mock_bklog_api.list_collectors.return_value = {
        "list": [{"collector_config_name_en": "dbm_dbactuator", "collector_config_id": 21}]
    }
    mock_bklog_api.run_databus_collectors.side_effect = ApiError("failed")

    operate_bklog_host_collectors(
        bk_host_ids=[101],
        action=OperateCollectorActionEnum.INSTALL.value,
        collector_names=["dbm_dbactuator", "not_exist"],
        bk_biz_id=9,
    )

    mock_bklog_api.run_databus_collectors.assert_called_once()
