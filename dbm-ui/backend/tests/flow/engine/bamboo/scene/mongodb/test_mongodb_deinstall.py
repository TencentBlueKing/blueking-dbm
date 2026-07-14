# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from backend.flow.engine.bamboo.scene.mongodb.mongodb_deinstall import MongoDBDeInstallFlow


def test_multi_cluster_deinstall_uses_serial_sub_pipelines():
    fake_builder = MagicMock()
    ticket_data = {
        "cluster_ids": [63, 64],
        "bk_biz_id": 3,
        "bk_app_abbr": "dba",
        "created_by": "admin",
    }

    with patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_deinstall.Builder",
        return_value=fake_builder,
    ), patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_deinstall.ActKwargs") as mock_act_kwargs_cls, patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_deinstall.deinstall",
        side_effect=lambda **kwargs: MagicMock(name=f"sub-{kwargs['cluster_id']}"),
    ) as mock_deinstall:
        mock_kwargs = MagicMock()
        mock_kwargs.payload = dict(ticket_data)
        mock_act_kwargs_cls.return_value = mock_kwargs

        MongoDBDeInstallFlow(root_id="root-1", data=ticket_data).multi_cluster_deinstall_flow()

    assert mock_deinstall.call_count == 2
    assert fake_builder.add_sub_pipeline.call_count == 2
    fake_builder.add_parallel_sub_pipeline.assert_not_called()
    fake_builder.run_pipeline.assert_called_once()
