# -*- coding: utf-8 -*-
import importlib

from django.utils.translation import gettext as _


def test_cross_switch_allows_backup_outside_zone():
    module = importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity_standalone")
    state, reasons = module.check_affinity_rules(
        disaster_tolerance_level=module.SAME_SUBZONE_CROSS_SWTICH,
        cluster_region=_("南京"),
        zone_list={"1"},
        actual_sub_zone_set={"1", "2"},
        actual_region_set={_("南京")},
        actual_rack_set={"11", "12", "99"},
        component_nodes=[
            {"actual_sub_zone": "1", "actual_rack": "11", "instance_role": "MONGO_DATA"},
            {"actual_sub_zone": "1", "actual_rack": "12", "instance_role": "MONGO_DATA"},
            {"actual_sub_zone": "2", "actual_rack": "99", "instance_role": "MONGO_BACKUP"},
        ],
    )
    assert state == module.NORMAL
    assert reasons == []


def test_cross_subzone_weak_allows_empty_zone_list():
    module = importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity_standalone")
    state, reasons = module.check_affinity_rules(
        disaster_tolerance_level=module.CROSS_SUBZONE_WEAK,
        cluster_region=_("南京"),
        zone_list=set(),
        actual_sub_zone_set={"1", "2"},
        actual_region_set={_("南京")},
        actual_rack_set={"11", "12"},
        component_nodes=[
            {"actual_sub_zone": "1", "actual_rack": "11"},
            {"actual_sub_zone": "2", "actual_rack": "12"},
        ],
    )
    assert state == module.NORMAL
    assert reasons == []


def test_print_result_sharded_only_mongos_when_only_mongos_issue(capsys):
    module = importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity_standalone")
    item = module.ClusterEval(
        cluster_id=1,
        domain="demo",
        cluster_type="MongoShardedCluster",
        cluster_region="shanghai",
        has_single_node_tag=False,
        affinity=module.CROSS_SUBZONE_WEAK,
        zone_list=set(),
        state=module.ABNORMAL,
        reasons=["[mongos] code=demo some mongos issue"],
        component_details=[
            {
                "set_name": "mongos",
                "zone_list": [],
                "actual_sub_zones": ["1"],
                "actual_regions": ["shanghai"],
                "actual_racks": ["11"],
                "nodes": [{"addr": "1.1.1.1:27017", "actual_sub_zone": "1", "actual_rack": "11", "instance_role": ""}],
                "state": module.ABNORMAL,
            },
            {
                "set_name": "shardsvr_group:0:127.0.0.1|0:127.0.0.2",
                "zone_list": [],
                "actual_sub_zones": ["1"],
                "actual_regions": ["shanghai"],
                "actual_racks": ["21"],
                "nodes": [
                    {"addr": "127.0.0.1:27017", "actual_sub_zone": "1", "actual_rack": "21", "instance_role": "m1"}
                ],
                "state": module.NORMAL,
            },
        ],
    )

    ret = module.print_result([item], summary_by_code=False)
    out = capsys.readouterr().out
    assert ret == 2
    assert "    - mongos " in out
    assert "shardsvr_group:" not in out
