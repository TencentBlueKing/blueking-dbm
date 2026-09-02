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

import { ClusterTypes } from '@common/const';

import { t } from '@locales/index';

import type { ISupportHostType } from '../types';

export const tabListMap: Record<ISupportHostType, string> = {
  [ClusterTypes.REDIS]: t('Redis 主机'),
  [ClusterTypes.SQLSERVER_HA]: t('SQLServer 主从主机'),
  [ClusterTypes.SQLSERVER_SINGLE]: t('SQLServer 单节点主机'),
  [ClusterTypes.TENDBCLUSTER]: t('TendbCluster 主机'),
  [ClusterTypes.TENDBHA]: t('MySQL 主从主机'),
  [ClusterTypes.TENDBSINGLE]: t('MySQL 单节点主机'),
};
