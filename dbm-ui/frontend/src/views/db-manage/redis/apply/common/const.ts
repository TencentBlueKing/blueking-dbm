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

import TendisCacheImg from '@images/tendis-cache.png';
import TendisClusterImg from '@images/tendis-cluster.png';
import TendisSSDImg from '@images/tendis-ssd.png';
import TendisplusImg from '@images/tendisplus.png';

// redis 服务器来源类型
export const redisIpSources = {
  resource_pool: {
    id: 'resource_pool',
    text: t('自动从资源池匹配'),
  },
  manual_input: {
    id: 'manual_input',
    text: t('业务空闲机'),
  },
};
export type RedisIpSources = keyof typeof redisIpSources;

// redis 部署架构
export const redisClusterTypes = {
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    text: 'TendisCache',
    tipContent: {
      img: TendisCacheImg,
      title: 'TendisCache',
      desc: t('TendisCache_支持高读写性能的集群Cache版本_Cache版本后端Redis主从对原理和社区一致'),
    },
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    text: 'TendisSSD',
    tipContent: {
      img: TendisSSDImg,
      title: 'TendisSSD',
      desc: t('TendisSSD_以RocksDB作为存储引擎_兼容Redis协议并配合SSD存储设备实现高性能持久化存储数据实时落地到磁盛'),
    },
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    text: 'Tendisplus',
    image: TendisplusImg,
    tipContent: {
      img: TendisplusImg,
      title: 'Tendisplus',
      desc: t('Tendisplus_TendisSSD的升级版本_完全兼容RedisCluster'),
    },
  },
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    text: 'RedisCluster',
    image: TendisClusterImg,
    tipContent: {
      img: TendisClusterImg,
      title: 'Redis Cluster',
      desc: t('原生 Redis Cluster'),
    },
  },
};
export type RedisClusterTypes = keyof typeof redisClusterTypes;
