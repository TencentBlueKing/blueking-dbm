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
import logging

from django.utils.translation import gettext as _

from backend.components.sql_import.client import SQLSimulationApi

logger = logging.getLogger("root")


def syntax_check_sql_impl(sqls: list, cluster_type: str, versions: list = None) -> dict:
    """
    Check SQL syntax against multiple MySQL versions.

    This function calls the DBM syntax_check_sql interface to validate SQL syntax
    against specified MySQL versions. If versions is not provided, it defaults to
    checking against 5.5, 5.6, 5.7, and 8.0.

    Args:
        sqls: List of SQL statements to check
        cluster_type: Cluster type for the SQL check
        versions: List of MySQL versions to check against. Defaults to ["5.5", "5.6", "5.7", "8.0"]

    Returns:
        dict: Raw response data from the syntax_check_sql interface

    Raises:
        Exception: When the interface call fails
    """
    # Set default versions if not provided
    if versions is None or len(versions) == 0:
        versions = ["5.5", "5.6", "5.7", "8.0"]
        logger.info(_("No versions provided, using default versions: {}").format(versions))

    # Prepare request parameters
    request_params = {"cluster_type": cluster_type, "versions": versions, "sqls": sqls}

    logger.info(
        _("Starting SQL syntax check. Cluster type: {}, Versions: {}, Number of SQL statements: {}").format(
            cluster_type, versions, len(sqls)
        )
    )

    try:
        # Call the syntax_check_sql interface
        result = SQLSimulationApi.syntax_check_sql(params=request_params, headers={"platform": "mcp"})

        logger.info(_("SQL syntax check completed successfully for {} statements").format(len(sqls)))
        return result
    except Exception as e:
        logger.error(
            _("SQL syntax check failed. Cluster type: {}, Versions: {}, Error: {}").format(
                cluster_type, versions, str(e)
            )
        )
        raise


def check_sql_file_grammar(cluster_type: str, path: str, file_list: list, versions: list = None) -> dict:
    """
    Check SQL file grammar against multiple MySQL versions.

    This function calls the DBM grammar_check interface to validate SQL syntax
    from files on the server. The execute_objects parameter is automatically
    constructed based on the file_list.

    Args:
        cluster_type: Cluster type for the SQL check
        path: Directory path where SQL files are located
        file_list: List of SQL file names to check
        versions: List of MySQL versions to check against. Defaults to ["5.5", "5.6", "5.7", "8.0"]

    Returns:
        dict: Raw response data from the grammar_check interface

    Raises:
        Exception: When the interface call fails
    """
    # Set default versions if not provided
    if versions is None or len(versions) == 0:
        versions = ["5.5", "5.6", "5.7", "8.0"]
        logger.info(_("No versions provided, using default versions: {}").format(versions))

    # Automatically construct execute_objects based on file_list
    execute_objects = [
        {
            "line_id": 1,
            "sql_files": file_list,
            "ignore_dbnames": [],
            "dbnames": [],
        }
    ]

    # Prepare request parameters
    request_params = {
        "cluster_type": cluster_type,
        "path": path,
        "files": file_list,
        "execute_objects": execute_objects,
    }

    logger.info(
        _("Starting SQL file grammar check. Cluster type: {}, Path: {}, Files: {}, Versions: {}").format(
            cluster_type, path, file_list, versions
        )
    )

    try:
        # Call the grammar_check interface
        result = SQLSimulationApi.grammar_check(params=request_params, headers={"platform": "mcp"})

        logger.info(_("SQL file grammar check completed successfully for {} files").format(len(file_list)))
        return result
    except Exception as e:
        logger.error(
            _("SQL file grammar check failed. Cluster type: {}, Path: {}, Files: {}, Error: {}").format(
                cluster_type, path, file_list, str(e)
            )
        )
        raise
