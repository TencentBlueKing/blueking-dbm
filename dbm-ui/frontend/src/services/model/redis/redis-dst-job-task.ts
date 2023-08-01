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
import { TransmissionTypes, WriteModes } from './redis-dst-history-job';

const failedTransmissions = [TransmissionTypes.FULL_TRANSFER_FAILED, TransmissionTypes.INCREMENTAL_TRANSFER_FAILED];
export default class RedisDSTJobTask {
  app: string;
  bill_id: number;
  bk_cloud_id: number;
  create_time: string;
  checked: boolean;
  dst_cluster: string;
  dts_server: string;
  fetch_file: string;
  id: number;
  ignore_errlist: string;
  is_src_logcount_restored: number;
  key_black_regex: string;
  key_white_regex: string;
  kill_syncer: number;
  message: string;
  resync_from_time: string;
  retry_times: number;
  sqlfile_dir: string;
  src_cluster: string;
  src_cluster_priority: number;
  src_dbsize: number;
  src_dbtype: string;
  src_have_list_keys: number;
  src_ip: string;
  src_ip_concurrency_limit: number;
  src_ip_zonename: string;
  src_kvstore_id: number;
  src_new_logcount: number;
  src_old_logcount: number;
  src_port: number;
  src_seg_end: number;
  src_seg_start: number;
  src_twemproxy_hash_tag_enabled: number;
  src_weight: number;
  status: TransmissionTypes;
  sync_operate: string;
  syncer_pid: number;
  syncer_port: number;
  task_type: string;
  tendis_binlog_lag: number;
  tendisbackup_file: string;
  update_time: string;
  user: string;
  write_mode: WriteModes;
  constructor(payload = {} as RedisDSTJobTask) {
    this.app = payload.app;
    this.bill_id = payload.bill_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.create_time = payload.create_time;
    this.checked = false;
    this.dst_cluster = payload.dst_cluster;
    this.dts_server = payload.dts_server;
    this.fetch_file = payload.fetch_file;
    this.id = payload.id;
    this.ignore_errlist = payload.ignore_errlist;
    this.is_src_logcount_restored = payload.is_src_logcount_restored;
    this.key_white_regex = payload.key_white_regex;
    this.key_black_regex = payload.key_black_regex;
    this.kill_syncer = payload.kill_syncer;
    this.message = payload.message;
    this.resync_from_time = payload.resync_from_time;
    this.retry_times = payload.retry_times;
    this.sqlfile_dir = payload.sqlfile_dir;
    this.src_cluster = payload.src_cluster;
    this.src_cluster_priority = payload.src_cluster_priority;
    this.src_dbsize = payload.src_dbsize;
    this.src_dbtype = payload.src_dbtype;
    this.src_have_list_keys = payload.src_have_list_keys;
    this.src_ip = payload.src_ip;
    this.src_ip_concurrency_limit = payload.src_ip_concurrency_limit;
    this.src_ip_zonename = payload.src_ip_zonename;
    this.src_kvstore_id = payload.src_kvstore_id;
    this.src_new_logcount = payload.src_new_logcount;
    this.src_old_logcount = payload.src_old_logcount;
    this.src_port = payload.src_port;
    this.src_seg_end = payload.src_seg_end;
    this.src_seg_start = payload.src_seg_start;
    this.src_twemproxy_hash_tag_enabled = payload.src_twemproxy_hash_tag_enabled;
    this.src_weight = payload.src_weight;
    this.status = payload.status;
    this.sync_operate = payload.status;
    this.syncer_pid = payload.syncer_pid;
    this.syncer_port = payload.syncer_port;
    this.task_type = payload.task_type;
    this.tendis_binlog_lag = payload.tendis_binlog_lag;
    this.tendisbackup_file = payload.status;
    this.update_time = payload.update_time;
    this.user = payload.user;
    this.write_mode = payload.write_mode;
  }

  get isFailedStatus() {
    return failedTransmissions.includes(this.status);
  }
}
