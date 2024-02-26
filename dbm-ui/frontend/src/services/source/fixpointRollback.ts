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

import FixpointLogModel from '@services/model/fixpoint-rollback/fixpoint-log';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

interface BackupLogRecord {
  backup_begin_time: string;
  backup_config_file: string;
  backup_consistent_time: string;
  backup_end_time: string;
  backup_host: string;
  backup_id: string;
  backup_meta_file: string;
  backup_port: string;
  backup_status: string;
  backup_time: string;
  backup_type: string;
  backup_dir: string;
  bill_id: string;
  binlog_info: {
    show_master_status: {
      binlog_file: string;
      binlog_pos: string;
      gtid: string;
      master_host: string;
      master_port: number;
    };
    show_slave_status: {
      binlog_file: string;
      binlog_pos: string;
      gtid: string;
      master_host: string;
      master_port: number;
    };
  };
  bk_biz_id: string;
  cluster_address: string;
  cluster_id: string;
  data_schema_grant: string;
  extra_fields: {
    backup_charset: string;
    encrypt_enable: boolean;
    storage_engine: string;
    time_zone: string;
    total_filesize: number;
    total_size_kb_uncompress: number;
    bk_cloud_id: number;
  };
  file_list: {
    contain_files: null;
    contain_tables: null;
    file_name: string;
    file_size: number;
    file_type: string;
    task_id: string;
  }[];
  index: {
    file_name: string;
  };
  instance_ip: string;
  instance_port: string;
  is_full_backup: string;
  mysql_role: string;
  mysql_version: string;
  server_id: string;
  shard_value: string;
}

const { currentBizId } = useGlobalBizs();

const path = `/apis/mysql/bizs/${currentBizId}/fixpoint_rollback`;

/**
 * 通过日志平台获取集群备份记录
 */
export function queryBackupLogFromBklog(params: {
  cluster_id: number
}) {
  return http.get<BackupLogRecord[]>(`${path}/query_backup_log_from_bklog/`, params);
}

/**
 * 根据job id查询任务执行状态和执行结果
 */
export function queryBackupLogFromLoacal(params: {
  cluster_id: number
}) {
  return http.get<BackupLogRecord[]>(`${path}/query_backup_log_from_local/`, params);
}

/**
 * 获取集群列表
 */
export function queryFixpointLog(params: {
  cluster_id: number,
  rollback_time: string,
  job_instance_id: number
}) {
  return http.get<ListBase<FixpointLogModel[]>>(`${path}/query_fixpoint_log/`, params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new FixpointLogModel(item)),
    }));
}

/**
 * 获取定点构造记录
 */
export function queryLatesBackupLog(params: {
  bk_biz_id: number,
  cluster_id: number,
  rollback_time: string,
  job_instance_id: number
}) {
  return http.get<{
    backup_logs: Array<any>,
    job_status: string,
    message: string
  }>(`${path}/query_latest_backup_log/`, params);
}
