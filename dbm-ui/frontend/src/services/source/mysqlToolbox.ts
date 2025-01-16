/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import http from '@services/http';

/**
 * 查询mysql版本升级可用版本列表
 */
export function queryMysqlHigherVersionPkgList(params: {
  cluster_id: number;
  higher_major_version?: boolean; // 代表是否跨版本升级, 默认false
  higher_all_version?: boolean; // 单节点本地升级 获取可用的升级包
}) {
  return http.post<
    {
      version: string;
      pkg_name: string;
      pkg_id: number;
    }[]
  >(`/apis/mysql/toolbox/query_higher_version_pkg_list/`, params);
}
