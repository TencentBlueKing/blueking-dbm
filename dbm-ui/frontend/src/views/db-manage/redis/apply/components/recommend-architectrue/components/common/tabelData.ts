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

export interface RowData {
  attribute: string;
  value: Record<
    string,
    {
      text: string;
      type?: 'advantage' | 'disadvantage' | 'developing';
      colspan?: number;
    }
  >;
}

export const tableData: RowData[] = [
  {
    attribute: t('涉及组件'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t('Twemproxy + 原生 Redis 主从'),
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: t('Twemproxy+ TendisSSD 主从'),
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: t('Predixy + TendisplusCluster(gossip 协议)'),
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: t('Predixy + RedisCluster(gossip 协议)'),
      },
    },
  },
  {
    attribute: t('数据保存位置'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t('内存'),
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: t('SSD 磁盘'),
        type: 'advantage',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: t('SSD 磁盘'),
        type: 'advantage',
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: t('内存'),
      },
    },
  },
  {
    attribute: t('访问方式'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t('方式一: 域名(指向 Proxy Ips), 普通 Redis 客户端;'),
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: t('方式一: 域名(指向 Proxy Ips), 普通 Redis 客户端;'),
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: t(
          '方式一: 域名(指向 Proxy Ips), 普通 Redis 客户端;\n方式二: 域名(指向 Redis Ips),  智能 Redis 客户端, 自动处理 moved 错误;',
        ),
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: t(
          '方式一: 域名(指向 Proxy Ips), 普通 Redis 客户端;\n方式二: 域名(指向Redis Ips),  智能 Redis 客户端, 自动处理 moved 错误;',
        ),
      },
    },
  },
  {
    attribute: t('命令支持'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t('a. 最新 Proxy 支持 Stream、Pubsub、事务;\nb. 支持 eval,key 需要满足 hash_tag 特性;'),
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: t(
          'a. 最新 Proxy 支持 Pubsub、事务, 不支持 Stream;\nb. 支持 eval,key 需要满足 hash_tag 特性;\nc. 不支持 scan、linsert、lrem 等命令;',
        ),
        type: 'disadvantage',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: t('a. Pubsub、事务、Stream 特性开发中;\nb. 支持 eval,key 需要满足 hash_tag 特性;'),
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: t('a. 支持 Stream、Pubsub,事务支持开发中;\nb. 支持eval,key 需要满足 hash_tag 特性;'),
      },
    },
  },
  {
    attribute: t('数据恢复'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t('只支持恢复到15天全备时间点'),
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: t('只支持恢复到15天全备时间点'),
        type: 'advantage',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: t('只支持恢复到15天全备时间点'),
        type: 'advantage',
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: t('只支持恢复到15天全备时间点'),
      },
    },
  },
  {
    attribute: t('推荐使用场景'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t('a. 缓存、QPS 要求较高、延迟要求较低;\nb. 同等数据规模,成本高;'),
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: t(
          'a. 数据量很大,且大部分是 set/get/hset/hget等 O(1) 请求场景;\nb. hgetall、smembers 等 O(n) 请求性能较差,推荐使用 hscan、sscan 等命令代替;\nc. zset类型性能支持很差，不推荐使用;\nd. 同等数据规模,成本低;\ne. 需要精确恢复数据;\nf. 版本已经不迭代, 只做紧急 Bug 修复;\ng.未来将关闭申请入口',
        ),
        type: 'disadvantage',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: t(
          'a. 数据量很大,且大部分是 set/get/hset/hget 等 O(1) 请求场景;\nb. hgetall、smembers 等 O(n) 请求性能较差, 推荐使用 hscan、sscan 等命令代替;\nc. zset 类型性能约为原生 Redis 1/5;\nd. 可通过智能客户端直连 TendisplusCluster, 减少一层代理转发,降低延迟;\ne. 同等数据规模,成本低;\nf. 需要精确恢复数据;\ng. 版本持续迭代中;',
        ),
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: t(
          'a. 缓存、QPS 要求较高、延迟要求较低;\nb.可通过智能客户端直连 RedisCluster, 使用原生 Redis 各种特性, 同时减少一层代理转发,降低延迟;\nc. 同等数据规模,成本高;',
        ),
        type: 'advantage',
      },
    },
  },
  {
    attribute: t('特别说明'),
    value: {
      [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
        text: t(
          '集群部署后，可在线切换为其他集群类型，注意事项:\n1. 切换过程中存量server连接会断开，需要程序需重连重试,持续时间1分钟内;\n2. 新集群类型 支持 老集群类型 相关特性;\n3. 如 TendisSSD 集群可在线切换为 TendisCache 集群和 Tendisplus 集群，但 TendisCache 集群不一定能切换为 TendisSSD 集群',
        ),
        type: 'advantage',
      },
      [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
        text: '',
      },
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
        text: '',
      },
      [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
        text: '',
      },
    },
  },
];
