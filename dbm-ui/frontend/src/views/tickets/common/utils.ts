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

import { format } from 'date-fns';

import type { NodesType } from '@services/types/ticket';

import type { IHostTableData } from '@components/cluster-common/big-data-host-table/HdfsHostTable.vue';

import { t } from '@locales/index';

/**
 * 单据状态类型
 */
export enum StatusTypes {
  ALL = '全部',
  PENDING = '审批中',
  RUNNING = '进行中',
  SUCCEEDED = '已完成',
  FAILED = '已终止',
  REVOKED = '已撤销',
}
export type StatusTypesStrings = keyof typeof StatusTypes;

/**
 * 状态 theme 映射
 */
export const tagTheme = {
  PENDING: 'warning',
  RUNNING: 'info',
  SUCCEEDED: 'success',
  FAILED: 'danger',
  REVOKED: 'danger',
  ALL: undefined,
};

/**
 * 获取状态对应文案
 * @param key 状态 key
 * @returns 状态文案
 */
export const getTagTheme = (key: StatusTypesStrings) => tagTheme[key] as BKTagTheme;

/**
 * 节点ip类型对应文案
 */
export const nodeTypeText: {
  [key: string]: string
} = {
  hot: t('热节点'),
  cold: t('冷节点'),
  master: 'Master',
  client: 'Client',
  datanode: 'DataNode',
  namenode: 'NameNode',
  zookeeper: 'Zookeeper',
  broker: 'Broker',
  proxy: 'Proxy',
  slave: 'Slave',
  bookkeeper: 'Bookkeeper',
};

/**
 * 获取节点IP列表
 * @param obj 节点对象
 * @returns 节点数组
 */
export function convertNodeFormat(obj: NodesType) {
  const nodeList: any = [];
  Object.entries(obj).forEach((item) => {
    const key = item[0];
    const value = item[1];
    if (value.length) {
      const data = value.map((key: IHostTableData) => key.ip);
      nodeList.push({ key, value: data });
    }
  });
  return nodeList;
}

/** 需要轮训的单据类型 */
export const needPollStatus = ['PENDING', 'RUNNING'];

/** flows colors */
export const flowsColors = {
  PENDING: 'warning',
  RUNNING: 'blue',
  SUCCEEDED: 'green',
  FAILED: 'red',
};

/** 格式化时间 */
export const getDate = (value: string) => format(new Date(value), 'yyyy-MM-dd');
