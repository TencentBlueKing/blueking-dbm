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

import { useGlobalBizs } from '@stores';

import http from './http';

/**
 * 获取集群 DB 名称
 */
export const getClusterDBNames = function (params: { cluster_ids: Array<number> }) {
  const { currentBizId } = useGlobalBizs();

  return http.post<
    Array<{
      cluster_id: number;
      databases: Array<string>;
      system_databases: Array<string>;
    }>
  >(`/apis/mysql/bizs/${currentBizId}/remote_service/show_cluster_databases/`, params);
};

// 校验flashback信息是否合法
export const checkFlashbackDatabase = function (params: {
  infos: Array<{
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
  }>;
}) {
  const { currentBizId } = useGlobalBizs();

  return http.post<
    {
      cluster_id: number;
      databases: string[];
      databases_ignore: string[];
      message: string;
      tables: string[];
      tables_ignore: string[];
    }[]
  >(`/apis/mysql/bizs/${currentBizId}/remote_service/check_flashback_database/`, params);
};

/**
 * 校验DB是否在集群内
 */
export const checkClusterDatabase = function (params: {
  infos: Array<{
    cluster_id: number;
    db_names: string[];
  }>;
}) {
  const { currentBizId } = useGlobalBizs();
  return http.post<
    {
      cluster_id: number;
      db_names: string[];
      check_info: Record<string, boolean>;
    }[]
  >(`/apis/mysql/bizs/${currentBizId}/remote_service/check_cluster_database/`, params);
};
