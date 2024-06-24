<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkTab
    v-model:active="moduleValue"
    class="top-tabs"
    type="unborder-card">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.name"
      :label="tab.label"
      :name="tab.name" />
  </BkTab>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { ClusterTypes } from '@common/const';

  interface TabItem {
    moduleId: ExtractedControllerDataKeys;
    label: string;
    name: ClusterTypes;
  }
  const { t } = useI18n();
  const tabs: TabItem[] = [
    {
      moduleId: 'mysql',
      label: t('MySQL 单节点'),
      name: ClusterTypes.TENDBSINGLE,
    },
    {
      moduleId: 'mysql',
      label: t('MySQL 主从'),
      name: ClusterTypes.TENDBHA,
    },
    {
      moduleId: 'mysql',
      label: 'TenDBCluster',
      name: ClusterTypes.TENDBCLUSTER,
    },
    {
      moduleId: 'redis',
      label: 'TendisplusCluster',
      name: ClusterTypes.TENDIS_PLUS_CLUSTER,
    },
    {
      moduleId: 'redis',
      label: 'TendisplusInstance',
      name: ClusterTypes.TENDIS_PLUS_INSTANCE,
    },
    {
      moduleId: 'redis',
      label: 'TendisSSDInstance',
      name: ClusterTypes.TENDIS_SSD_INSTANCE,
    },
    // {
    //   moduleId: 'redis',
    //   label: 'Redis',
    //   name: ClusterTypes.REDIS,
    // },
    {
      moduleId: 'redis',
      label: 'RedisCluster',
      name: ClusterTypes.REDIS_CLUSTER,
    },
    {
      moduleId: 'redis',
      label: t('Redis 主从'),
      name: ClusterTypes.REDIS_INSTANCE,
    },
    {
      moduleId: 'redis',
      label: t('Redis 分片'),
      name: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    },
    {
      moduleId: 'redis',
      label: 'Tendisplus',
      name: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    },
    {
      moduleId: 'redis',
      label: 'Redis',
      name: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    },
    {
      moduleId: 'redis',
      label: 'Twemproxy',
      name: ClusterTypes.TWEMPROXY_TENDISPLUS_INSTANCE,
    },
    {
      moduleId: 'redis',
      label: 'TendisSSD',
      name: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    },
    // {
    //   moduleId: 'mongodb',
    //   label: 'MongoDB',
    //   name: ClusterTypes.MONGODB,
    // },
    {
      moduleId: 'mongodb',
      label: 'MongoCluster',
      name: ClusterTypes.MONGOCLUSTER,
    },
    {
      moduleId: 'mongodb',
      label: t('MongoDB 副本集'),
      name: ClusterTypes.MONGO_REPLICA_SET,
    },
    {
      moduleId: 'mongodb',
      label: t('MongoDB 分片集'),
      name: ClusterTypes.MONGO_SHARED_CLUSTER,
    },
    {
      moduleId: 'sqlserver',
      label: t('SQLServer 单节点'),
      name: ClusterTypes.SQLSERVER_SINGLE,
    },
    {
      moduleId: 'sqlserver',
      label: t('SQLServer 主从'),
      name: ClusterTypes.SQLSERVER_HA,
    },
    {
      moduleId: 'bigdata',
      label: 'ES',
      name: ClusterTypes.ES,
    },
    {
      moduleId: 'bigdata',
      label: 'Kafka',
      name: ClusterTypes.KAFKA,
    },
    {
      moduleId: 'bigdata',
      label: 'HDFS',
      name: ClusterTypes.HDFS,
    },
    {
      moduleId: 'bigdata',
      label: 'Pulsar',
      name: ClusterTypes.PULSAE,
    },
    {
      moduleId: 'bigdata',
      label: 'InfluxDB',
      name: ClusterTypes.INFLUXDB,
    },
    {
      moduleId: 'bigdata',
      label: 'Riak',
      name: ClusterTypes.RIAK,
    },
  ];

  const funControllerStore = useFunController();

  const moduleValue = defineModel<ClusterTypes>({
    default: ClusterTypes.TENDBSINGLE,
  });

  const renderTabs = tabs.filter((item) => {
    const { moduleId, name: clusterType } = item;
    const data = funControllerStore.funControllerData[moduleId];
    // 整个模块没有开启
    if (!data || data.is_enabled !== true) {
      return false;
    }
    if (clusterType === item.moduleId && data.is_enabled) {
      return true;
    }
    const children = data.children as Record<ClusterTypes, ControllerBaseInfo>;
    return children[clusterType] && children[clusterType]?.is_enabled;
  });
</script>

<style lang="less">
  .top-tabs {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content {
      display: none;
    }
  }
</style>
