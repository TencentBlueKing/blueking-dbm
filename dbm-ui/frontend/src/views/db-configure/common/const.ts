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

import { ClusterTypes, DBTypes } from '@common/const';

import { t } from '@locales/index';

import type { ExtraClusterConf, ExtraParamertesCluster } from './types';

/**
 * 有多份配置的集群
 */
export const extraParamertesCluster: ExtraParamertesCluster = {
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: [
    {
      conf_type: 'proxyconf',
      data: null,
      loading: false,
      title: t('Proxy_参数配置'),
      version: 'Predixy-latest',
    },
  ],
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: [
    {
      conf_type: 'proxyconf',
      data: null,
      loading: false,
      title: t('Proxy_参数配置'),
      version: 'Twemproxy-latest',
    },
  ],
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: [
    {
      conf_type: 'proxyconf',
      data: null,
      loading: false,
      title: t('Proxy_参数配置'),
      version: 'Twemproxy-latest',
    },
  ],
};

/**
 * 默认配置 title 映射
 */
export const defaultConfTitles: Partial<Record<ClusterTypes, string>> = {
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: t('Redis_配置'),
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: t('Redis_配置'),
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: t('Redis_配置'),
};

/**
 * 所有集群的默认配置
 */
export const getDefaultConf = (type: ClusterTypes, name = t('参数配置')) => ({
  confType: 'dbconf',
  name: defaultConfTitles[type] || name,
});

/**
 * 集群额外配置集合
 */
export const extraClusterConfs: ExtraClusterConf = {
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: [
    {
      confType: 'proxyconf',
      name: t('Proxy_配置'),
    },
  ],
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: [
    {
      confType: 'proxyconf',
      name: t('Proxy_配置'),
    },
  ],
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: [
    {
      confType: 'proxyconf',
      name: t('Proxy_配置'),
    },
  ],
};

/**
 * 交互上没有模块级别配置的集群
 */
export const notModuleClusters = [
  DBTypes.REDIS,
  DBTypes.ES,
  DBTypes.KAFKA,
  DBTypes.HDFS,
  DBTypes.MONGODB,
  DBTypes.DORIS,
];
