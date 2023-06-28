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
    v-model:active="curTab"
    class="top-tabs"
    type="unborder-card"
    @change="handleChangeClusterType">
    <BkTabPanel
      v-for="tab of tabs"
      :key="tab.name"
      :label="tab.label"
      :name="tab.name" />
  </BkTab>
  <div
    :key="curTab"
    class="resource-spec-page">
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
      :cluster-type="curTab"
      :cluster-type-label="clusterTypeLabel"
      :machine-type="curChildTab"
      :machine-type-label="machineTypeLabel" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import SpecList from '../components/SpecList.vue';

  const { t } = useI18n();
  const route = useRoute();

  const curTab = ref<string>(ClusterTypes.TENDBSINGLE);
  const curChildTab = ref('');
  const tabs = [
    {
      label: t('MySQL单节点'),
      name: ClusterTypes.TENDBSINGLE,
      children: [
        {
          label: t('后端存储机型'),
          name: 'single',
        },
      ],
    },
    {
      label: t('MySQL高可用'),
      name: ClusterTypes.TENDBHA,
      children: [
        {
          label: t('后端存储机型'),
          name: 'backend',
        },
        {
          label: t('Proxy机型'),
          name: 'proxy',
        },
      ],
    },
    {
      label: 'TendisCache',
      name: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      children: [
        {
          label: t('后端存储机型'),
          name: 'tendiscache',
        },
        {
          label: t('Proxy机型'),
          name: 'twemproxy',
        },
      ],
    },
    {
      label: 'TendisSSD',
      name: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      children: [
        {
          label: t('后端存储机型'),
          name: 'tendisssd',
        },
        {
          label: t('Proxy机型'),
          name: 'twemproxy',
        },
      ],
    },
    {
      label: 'TendisPlus',
      name: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      children: [
        {
          label: t('后端存储机型'),
          name: 'tendisplus',
        },
        {
          label: t('Proxy机型'),
          name: 'predixy',
        },
      ],
    },
    {
      label: 'ES',
      name: ClusterTypes.ES,
      children: [
        {
          label: t('Master节点规格'),
          name: 'es_master',
        },
        {
          label: t('Client节点规格'),
          name: 'es_client',
        },
        {
          label: t('冷_热节点规格'),
          name: 'es_datanode',
        },
      ],
    },
    {
      label: 'HDFS',
      name: ClusterTypes.HDFS,
      children: [
        {
          label: t('DataNode节点规格'),
          name: 'hdfs_datanode',
        },
        {
          label: t('NameNode_Zookeeper_JournalNode节点规格'),
          name: 'hdfs_master',
        },
      ],
    },
    {
      label: 'Kafka',
      name: ClusterTypes.KAFKA,
      children: [
        {
          label: t('Zookeeper节点规格'),
          name: 'zookeeper',
        },
        {
          label: t('Broker节点规格'),
          name: 'broker',
        },
      ],
    },
    {
      label: 'InfluxDB',
      name: ClusterTypes.INFLUXDB,
      children: [
        {
          label: t('后端存储机型'),
          name: 'influxdb',
        },
      ],
    },
    {
      label: 'Pulsar',
      name: ClusterTypes.PULSAE,
      children: [
        {
          label: t('Bookkeeper节点规格'),
          name: 'pulsar_bookkeeper',
        },
        {
          label: t('Zookeeper节点规格'),
          name: 'pulsar_zookeeper',
        },
        {
          label: t('Broker节点规格'),
          name: 'pulsar_broker',
        },
      ],
    },
  ];
  const childrenTabs = computed(() => tabs.find(item => item.name === curTab.value)?.children || []);
  const clusterTypeLabel = computed(() => tabs.find(item => item.name === curTab.value)?.label ?? '');
  const machineTypeLabel = computed(() => childrenTabs.value.find(item => item.name === curChildTab.value)?.label ?? '');

  const handleChangeClusterType = (value: string) => {
    if (curTab.value !== value) {
      curChildTab.value = '';
    }
  };

  onBeforeMount(() => {
    const { spec_cluster_type: clusterType } = route.query;
    if (clusterType) {
      curTab.value = clusterType as string;
    }
  });
</script>

<style lang="less" scoped>
  .resource-spec-page {
    padding-top: 42px;

    :deep(.bk-tab-content) {
      padding: 0;
    }
  }
</style>
