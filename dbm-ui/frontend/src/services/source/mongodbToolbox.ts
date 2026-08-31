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
import GrammarCheckModel from '@services/model/sql-import/grammar-check';
import type { ListBase, MachineRelatedInstance } from '@services/types';

import { getSQLFilename } from '@utils';

const getRootPath = (bizId = window.PROJECT_CONFIG.BIZ_ID) => `/apis/mongodb/bizs/${bizId}/toolbox`;

/**
 * 执行集群来源指令
 */
export function executeClusterTcpCmd(params: { cluster_ids: number[] }) {
  return http.post<{
    job_instance_id: number;
    job_instance_name: string;
    step_instance_id: number;
  }>(`${getRootPath()}/execute_cluster_tcp_cmd/`, params);
}

/**
 * 查询集群来源结果
 */
export function getClusterNetTcpResult(params: { job_instance_id: number }) {
  return http.post<{
    data: {
      cluster_domain: string;
      error: string[];
      report: {
        all_connections: number;
        bak_operator: string;
        cluster_domain: string;
        establish: number;
        operator: string;
        remote_ip: string;
        topo?: string[];
      }[];
      success: string[];
    }[];
    finished: boolean;
  }>(`${getRootPath()}/get_cluster_net_tcp_result/`, params);
}

/**
 * 查询分片信息
 */
export function getMongoShard(params: {
  bk_biz_id: number;
  cluster_id?: number;
  limit?: number;
  offset?: number;
  shard_names?: string; // 逗号分隔
}) {
  return http.get<
    ListBase<
      {
        cluster_id: number;
        disaster_tolerance_level: string;
        major_version: string;
        master_domain: string;
        region: string;
        related_instance: MachineRelatedInstance[];
        shard_name: string;
        shard_node_count: number;
      }[]
    >
  >(`${getRootPath()}/get_mongo_shard/`, params);
}

/**
 * 查询集群分片列表（缩容分片数下拉数据源）
 */
export function listClusterShards(params: { cluster_ids: number[] }) {
  return http.get<
    {
      cluster_id: number;
      immute_domain: string;
      shard_list: string[];
    }[]
  >(`${getRootPath()}/list_cluster_shards/`, params);
}

/**
 * MongoDB: 查询集群可升级版本列表
 */
export function listAvailableMongoVersions(params: { cluster_ids: number[] }) {
  return http.get<
    {
      full_list: string[];
      major: string;
    }[]
  >(`${getRootPath()}/list_available_versions/`, params);
}

/**
 * 脚本检查
 */
export function checkMongoScriptSyntax(params: FormData) {
  return http.post(`${getRootPath()}/check_mongo_script_syntax/`, params).then<Record<string, GrammarCheckModel>>(
    (
      data: {
        raw_file_name: string;
        script_content: string;
        script_path: string;
      }[],
    ) =>
      data.reduce(
        (result, item) => ({
          ...result,
          [getSQLFilename(item.raw_file_name)]: new GrammarCheckModel({
            content: item.script_content,
            raw_file_name: item.raw_file_name,
            sql_path: item.script_path,
          } as GrammarCheckModel),
        }),
        {} as Record<string, GrammarCheckModel>,
      ),
  );
}
