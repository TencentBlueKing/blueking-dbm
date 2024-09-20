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
  <div class="resource-spec-list-page">
    <DbTab v-model="curTab" />
    <div
      :key="curTab"
      class="wrapper">
      <BkTab
        v-model:active="curChildTab"
        type="card">
        <BkTabPanel
          v-for="childTab of childrenTabs"
          :key="childTab.name"
          :label="childTab.label"
          :name="childTab.name" />
      </BkTab>
      <SpecList
        :db-type="curTab"
        :db-type-label="clusterTypeLabel"
        :machine-type="curChildTab"
        :machine-type-label="machineTypeLabel" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import SpecList from './components/SpecList.vue';

  interface TabItem {
    moduleId: ExtractedControllerDataKeys;
    label: string;
    name: string;
    children: {
      label: string;
      name: string;
    }[];
  }

  const { t } = useI18n();
  const route = useRoute();
  const funControllerStore = useFunController();

  const tabs: TabItem[] = [
    {
      moduleId: 'mysql',
      label: 'MySql',
      name: DBTypes.MYSQL,
      children: [
        {
          label: 'Proxy',
          name: 'proxy',
        },
        {
          label: t('后端存储'),
          name: 'backend',
        },
      ],
    },
    {
      moduleId: 'mysql',
      label: 'TenDBCluster',
      name: DBTypes.TENDBCLUSTER,
      children: [
        {
          label: t('接入层Master'),
          name: 'proxy',
        },
        {
          label: t('后端存储规格'),
          name: 'backend',
        },
      ],
    },
    {
      moduleId: 'redis',
      label: 'Redis',
      name: DBTypes.REDIS,
      children: [
        {
          label: 'Proxy',
          name: 'proxy',
        },
        {
          label: t('TendisCache后端存储'),
          name: 'TwemproxyRedisInstance',
        },
        {
          label: t('TendisSSD后端存储'),
          name: 'TwemproxyTendisSSDInstance',
        },
        {
          label: t('TendisPlus后端存储'),
          name: 'PredixyTendisplusCluster',
        },
        {
          label: 'RedisCluster',
          name: 'PredixyRedisCluster',
        },
        {
          label: t('Redis主从'),
          name: 'RedisInstance',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'ES',
      name: DBTypes.ES,
      children: [
        {
          label: t('Master节点'),
          name: 'es_master',
        },
        {
          label: t('Client节点'),
          name: 'es_client',
        },
        {
          label: t('冷_热节点'),
          name: 'es_datanode',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'HDFS',
      name: DBTypes.HDFS,
      children: [
        {
          label: t('DataNode节点'),
          name: 'hdfs_datanode',
        },
        {
          label: t('NameNode_Zookeeper_JournalNode节点'),
          name: 'hdfs_master',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'Kafka',
      name: DBTypes.KAFKA,
      children: [
        {
          label: t('Zookeeper节点'),
          name: 'zookeeper',
        },
        {
          label: t('Broker节点'),
          name: 'broker',
        },
      ],
    },
    // {
    //   moduleId: 'bigdata',
    //   label: 'InfluxDB',
    //   name: ClusterTypes.INFLUXDB,
    //   children: [
    //     {
    //       label: t('后端存储机型'),
    //       name: 'influxdb',
    //     },
    //   ],
    // },
    {
      moduleId: 'bigdata',
      label: 'Pulsar',
      name: DBTypes.PULSAR,
      children: [
        {
          label: t('Bookkeeper节点'),
          name: 'pulsar_bookkeeper',
        },
        {
          label: t('Zookeeper节点'),
          name: 'pulsar_zookeeper',
        },
        {
          label: t('Broker节点'),
          name: 'pulsar_broker',
        },
      ],
    },
    {
      moduleId: 'bigdata',
      label: 'Riak',
      name: DBTypes.RIAK,
      children: [
        {
          label: t('后端存储'),
          name: 'riak',
        },
      ],
    },
    {
      moduleId: 'mongodb',
      label: 'MongoDB',
      name: DBTypes.MONGODB,
      children: [
        {
          label: 'ConfigSvr',
          name: 'mongo_config',
        },
        {
          label: 'Mongos',
          name: 'mongos',
        },
        {
          label: t('副本集/ShardSvr'),
          name: 'mongodb',
        },
      ],
    },
    {
      moduleId: 'sqlserver',
      label: 'SQLServer',
      name: DBTypes.SQLSERVER,
      children: [
        {
          label: t('后端存储'),
          name: 'sqlserver',
        },
      ],
    },
  ];

  const curTab = ref(DBTypes.MYSQL);
  const curChildTab = ref('');

  const renderTabs = computed(() =>
    tabs.filter((item) => {
      const data = funControllerStore.funControllerData[item.moduleId];
      if (!data) {
        return false;
      }

      const childItem = (data.children as Record<TabItem['name'], ControllerBaseInfo>)[item.name];

      // 若有对应的模块子功能，判断是否开启
      if (childItem) {
        return data && data.is_enabled && childItem.is_enabled;
      }

      // 若无，则判断整个模块是否开启
      return data && data.is_enabled;
    }),
  );
  const childrenTabs = computed(() => renderTabs.value.find((item) => item.name === curTab.value)?.children || []);
  const clusterTypeLabel = computed(() => renderTabs.value.find((item) => item.name === curTab.value)?.label ?? '');
  const machineTypeLabel = computed(
    () => childrenTabs.value.find((item) => item.name === curChildTab.value)?.label ?? '',
  );

  watch(curTab, (newVal, oldVal) => {
    if (oldVal !== newVal) {
      curChildTab.value = '';
    }
  });

  onMounted(() => {
    const { spec_cluster_type: clusterType } = route.query;
    if (clusterType) {
      curTab.value = clusterType as DBTypes;
    }
  });
</script>
<style lang="less">
  .resource-spec-list-page {
    .bk-tab-content {
      display: none;
    }

    .top-tabs {
      padding: 0 24px;
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);
    }

    .wrapper {
      padding: 24px;
    }
  }
</style>
