"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from rest_framework.response import Response

from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class SqlserverSingleApplySceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_single_apply
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.single_cluster_apply_scene()
        return Response({"root_id": root_id})


class SqlserverHAApplySceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_ha_apply
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.ha_cluster_apply_scene()
        return Response({"root_id": root_id})


class SqlserverSQLFileExecuteSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_sql_file_execute
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.sql_file_execute_scene()
        return Response({"root_id": root_id})


class SqlserverBackupDBSSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_backup_dbs
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.backup_dbs_scene()
        return Response({"root_id": root_id})


class SqlserverRenameDBSSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/rename_backup_dbs
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.rename_dbs_scene()
        return Response({"root_id": root_id})


class SqlserverCleanDBSSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/clean_backup_dbs
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.clean_dbs_scene()
        return Response({"root_id": root_id})


class SqlserverHASwitchSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_ha_switch
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.ha_switch_scene()
        return Response({"root_id": root_id})


class SqlserverHAFailOverSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_ha_fail_over
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.ha_fail_over_scene()
        return Response({"root_id": root_id})


class SqlserverDBBuildSyncSceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/sqlserver_build_db_sync
        params:
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = SqlserverController(root_id=root_id, ticket_data=request.data)
        test.ha_build_db_sync_scene()
        return Response({"root_id": root_id})
