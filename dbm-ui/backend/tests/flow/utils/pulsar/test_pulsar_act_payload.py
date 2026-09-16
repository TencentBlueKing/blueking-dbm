# -*- coding: utf-8 -*-
"""Pulsar actuator payload 的配置查询测试。"""

from backend.flow.consts import LevelInfoEnum, PulsarRoleEnum
from backend.flow.utils.pulsar import pulsar_act_payload as mod
from backend.ticket.constants import TicketType


def test_existing_cluster_config_query_includes_default_tendata_module(monkeypatch):
    """已有集群单据须带上模块层级，dbconfig 才能解析 cluster 的父级。"""
    captured_params = {}

    def fake_query_conf_item(params):
        captured_params.update(params)
        return {
            "content": {
                PulsarRoleEnum.ZooKeeper: {},
                PulsarRoleEnum.BookKeeper: {},
                PulsarRoleEnum.Broker: {},
            }
        }

    monkeypatch.setattr(mod.DBConfigApi, "query_conf_item", fake_query_conf_item)

    mod.PulsarActPayload(
        {
            "ticket_type": TicketType.PULSAR_DISABLE.value,
            "bk_biz_id": 3,
            "domain": "pulsar.example.db",
            "db_version": "2.10.1",
        }
    )

    assert captured_params["level_info"] == {"module": LevelInfoEnum.TendataModuleDefault}
