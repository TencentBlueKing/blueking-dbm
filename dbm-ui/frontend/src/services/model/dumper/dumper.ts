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
import dayjs from 'dayjs';

import { t } from '@locales/index';
export default class Dumper {
  static TBINLOGDUMPER_REDUCE_NODES = 'TBINLOGDUMPER_REDUCE_NODES'; // 下架
  static TBINLOGDUMPER_SWITCH_NODES = 'TBINLOGDUMPER_SWITCH_NODES'; // 切换
  static TBINLOGDUMPER_ENABLE_NODES = 'TBINLOGDUMPER_ENABLE_NODES'; // 启用
  static TBINLOGDUMPER_DISABLE_NODES = 'TBINLOGDUMPER_DISABLE_NODES'; // 禁用

  static operationIconMap = {
    [Dumper.TBINLOGDUMPER_REDUCE_NODES]: 'shanchuzhong',
    [Dumper.TBINLOGDUMPER_SWITCH_NODES]: 'qianyizhong',
    [Dumper.TBINLOGDUMPER_ENABLE_NODES]: 'qiyongzhong',
    [Dumper.TBINLOGDUMPER_DISABLE_NODES]: 'jinyongzhong',
  };

  static operationTextMap = {
    [Dumper.TBINLOGDUMPER_REDUCE_NODES]: t('删除任务进行中'),
    [Dumper.TBINLOGDUMPER_SWITCH_NODES]: t('迁移任务进行中'),
    MYSQL_MASTER_SLAVE_SWITCH: t('迁移任务进行中'),
    MYSQL_MASTER_FAIL_OVER: t('迁移任务进行中'),
    [Dumper.TBINLOGDUMPER_ENABLE_NODES]: t('启用任务进行中'),
    [Dumper.TBINLOGDUMPER_DISABLE_NODES]: t('禁用任务进行中'),
  };

  add_type: string;
  area_name: number;
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_id: number;
  create_at: string;
  creator: string;
  dumper_config: {
    bk_biz_id: number;
    creator: string;
    id: number;
    name: string;
    receiver: string;
    receiver_type: string;
    subscribe: {
      db_name: string;
      table_names: string[];
    };
    updater: string;
  };
  dumper_id: number;
  id: number;
  ip: string;
  listen_port: number;
  need_transfer: true;
  operation: {
    ticket_type?: string;
    ticket_id?: number;
  };
  phase: string;
  proc_type: string;
  protocol_type: string;
  source_cluster?: {
    bk_cloud_id: number;
    cluster_type: string;
    id: number;
    immute_domain: string;
    major_version: string;
    master_ip: string;
    master_port: number;
    name: string;
    region: string;
  };
  target_address: string;
  target_port: number;
  update_at: string;
  updater: string;
  version: string;

  constructor(payload = {} as Dumper) {
    this.add_type = payload.add_type;
    this.area_name = payload.area_name;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.cluster_id = payload.cluster_id;
    this.creator = payload.creator;
    this.create_at = payload.create_at;
    this.dumper_config = payload.dumper_config;
    this.dumper_id = payload.dumper_id;
    this.id = payload.id;
    this.ip = payload.ip;
    this.listen_port = payload.listen_port;
    this.need_transfer = payload.need_transfer;
    this.operation = payload.operation;
    this.phase = payload.phase;
    this.proc_type = payload.proc_type;
    this.protocol_type = payload.protocol_type;
    this.source_cluster = payload.source_cluster;
    this.target_address = payload.target_address;
    this.target_port = payload.target_port;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.version = payload.version;
    console.log('prig model = ', this);
  }

  // 操作中的状态
  get operationRunningStatus() {
    return this.operation.ticket_type ?? '';
  }

  // 操作中的状态描述文本
  get operationStatusText() {
    return Dumper.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的按钮状态提示文本
  get operationBtnTipStatusText() {
    return `${Dumper.operationTextMap[this.operationRunningStatus]}，${t('无法操作')}`;
  }

  // 操作中的状态 icon
  get operationStatusIcon() {
    return Dumper.operationIconMap[this.operationRunningStatus];
  }

  // 操作中的单据 ID
  get operationTicketId() {
    return this.operation.ticket_id ?? 0;
  }

  get isRunning() {
    return this.phase === 'online';
  }

  get isOperating() {
    return Boolean(this.operation.ticket_type);
  }

  get isNew() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get operationTagTip() {
    return ({
      icon: Dumper.operationIconMap[this.operation?.ticket_type ?? ''],
      tip: Dumper.operationTextMap[this.operation?.ticket_type ?? ''],
      ticketId: this.operation?.ticket_id ?? 0,
    });
  }
}
