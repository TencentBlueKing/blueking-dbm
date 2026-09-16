# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from backend.db_meta.api.cluster.pulsar.enable import enable
from backend.db_meta.enums import ClusterPhase, ClusterStatus


@patch("backend.db_meta.api.cluster.pulsar.enable.Cluster.objects.get")
def test_enable_restores_cluster_phase_and_status(mock_get):
    cluster = MagicMock()
    mock_get.return_value = cluster

    enable(cluster_id=152)

    mock_get.assert_called_once_with(id=152)
    assert cluster.phase == ClusterPhase.ONLINE.value
    assert cluster.status == ClusterStatus.NORMAL.value
    cluster.save.assert_called_once_with()
