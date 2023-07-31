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

export enum CopyModes {
  INTRA_BISNESS = 'one_app_diff_cluster', // 业务内
  CROSS_BISNESS = 'diff_app_diff_cluster', // 跨业务
  INTRA_TO_THIRD = 'copy_to_other_system', // 业务内至第三方
  SELFBUILT_TO_INTRA = 'user_built_to_dbm', // 自建集群至业务内
}

export enum WriteModes {
  DELETE_AND_WRITE_TO_REDIS = 'delete_and_write_to_redis', // 先删除同名redis key，再执行写入 (如: del $key + hset $key)
  KEEP_AND_APPEND_TO_REDIS = 'keep_and_append_to_redis', // 保留同名redis key，追加写入
  FLUSHALL_AND_WRITE_TO_REDIS = 'flushall_and_write_to_redis', // 先清空目标集群所有数据，再写入
}

export enum DisconnectModes {
  AUTO_DISCONNECT_AFTER_REPLICATION = 'auto_disconnect_after_replication', // 复制完成后，自动断开
  KEEP_SYNC_WITH_REMINDER = 'keep_sync_with_reminder', // 不断开，定时发送断开提醒
}

export enum RemindFrequencyModes {
  ONCE_DAILY = 'once_daily', // 一天一次
  ONCE_WEEKLY = 'once_weekly', // 一周一次
}

export enum RepairAndVerifyModes {
  DATA_CHECK_AND_REPAIR = 'data_check_and_repair', // 数据校验并修复
  DATA_CHECK_ONLY = 'data_check_only', // 仅进行数据校验，不进行修复
  NO_CHECK_NO_REPAIR = 'no_check_no_repair', // 不校验不修复
}


export enum RepairAndVerifyFrequencyModes {
  ONCE_AFTER_REPLICATION = 'once_after_replication', // 复制完成后，只进行一次
  ONCE_EVERY_THREE_DAYS = 'once_every_three_days', // 复制完成后，每三天一次
  ONCE_WEEKLY = 'once_weekly', // 复制完成后，每周一次
}

export default class RedisDSTHistoryJob {
  app: string;
  bill_id: number;
  bk_cloud_id: number;
  create_time: string;
  dts_bill_type: string;
  dts_copy_type: CopyModes;
  dst_bk_biz_id: string;
  dst_cluster: string;
  dst_cluster_id: number;
  dst_cluster_type: string;
  data_check_repair_type: RepairAndVerifyModes;
  data_check_repair_execution_frequency: RepairAndVerifyFrequencyModes;
  failed_cnt: number;
  id: number;
  key_white_regex: string;
  key_black_regex: string;
  last_data_check_repair_flow_id: string;
  last_data_check_repair_flow_execute_time: string;
  online_switch_type: string;
  running_cnt: number;
  sync_disconnect_type: DisconnectModes;
  sync_disconnect_reminder_frequency: RemindFrequencyModes;
  src_cluster: string;
  src_cluster_id: number;
  src_cluster_type: string;
  src_rollback_bill_id: number;
  success_cnt: number;
  status: number;
  total_cnt: number;
  to_exec_cnt: number;
  update_time: string;
  user: string;
  write_mode: WriteModes;
  constructor(payload = {} as RedisDSTHistoryJob) {
    this.app = payload.app;
    this.bill_id = payload.bill_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.create_time = payload.create_time;
    this.dts_bill_type = payload.dts_bill_type;
    this.dts_copy_type = payload.dts_copy_type;
    this.dst_bk_biz_id = payload.dst_bk_biz_id;
    this.dst_cluster = payload.dst_cluster;
    this.dst_cluster_id = payload.dst_cluster_id;
    this.dst_cluster_type = payload.dst_cluster_type;
    this.data_check_repair_type = payload.data_check_repair_type;
    this.data_check_repair_execution_frequency = payload.data_check_repair_execution_frequency;
    this.failed_cnt = payload.failed_cnt;
    this.id = payload.id;
    this.key_white_regex = payload.key_white_regex;
    this.key_black_regex = payload.key_black_regex;
    this.last_data_check_repair_flow_id = payload.last_data_check_repair_flow_id;
    this.last_data_check_repair_flow_execute_time = payload.last_data_check_repair_flow_execute_time;
    this.online_switch_type = payload.online_switch_type;
    this.running_cnt = payload.running_cnt;
    this.sync_disconnect_type = payload.sync_disconnect_type;
    this.sync_disconnect_reminder_frequency = payload.sync_disconnect_reminder_frequency;
    this.src_cluster = payload.src_cluster;
    this.src_cluster_id = payload.src_cluster_id;
    this.src_cluster_type = payload.src_cluster_type;
    this.src_rollback_bill_id = payload.src_rollback_bill_id;
    this.success_cnt = payload.success_cnt;
    this.status = payload.status;
    this.total_cnt = payload.total_cnt;
    this.to_exec_cnt = payload.to_exec_cnt;
    this.update_time = payload.update_time;
    this.user = payload.user;
    this.write_mode = payload.write_mode;
  }
}
