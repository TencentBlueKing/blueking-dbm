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
  <div class="ticket-flow-list-page">
    <BkTab
      v-model:active="curTab"
      class="top-tabs"
      type="unborder-card"
      @change="handleChangeClusterType">
      <BkTabPanel
        v-for="tab of renderTabs"
        :key="tab.name"
        :label="tab.label"
        :name="tab.name" />
    </BkTab>
    <List :active-db-type="curTab" />
  </div>
</template>
<script setup lang="ts">
  import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { ClusterTypes, DBTypes } from '@common/const';

  import List from './components/List.vue';

  const route = useRoute();
  const funControllerStore = useFunController();

  const tabs = [
    {
      moduleId: 'mysql',
      label: 'Mysql',
      name: DBTypes.MYSQL,
    },
    {
      moduleId: 'redis',
      label: 'Redis',
      name: DBTypes.REDIS,
    },
    {
      moduleId: 'bigdata',
      label: 'ES',
      name: ClusterTypes.ES,
    },
    {
      moduleId: 'bigdata',
      label: 'HDFS',
      name: ClusterTypes.HDFS,
    },
    {
      moduleId: 'bigdata',
      label: 'Kafka',
      name: ClusterTypes.KAFKA,
    },
    {
      moduleId: 'bigdata',
      label: 'InfluxDB',
      name: ClusterTypes.INFLUXDB,
    },
    {
      moduleId: 'bigdata',
      label: 'Pulsar',
      name: ClusterTypes.PULSAE,
    },
    {
      moduleId: 'mysql',
      label: 'TenDBCluster',
      name: ClusterTypes.TENDBCLUSTER,
    },
  ];

  const curTab = ref<string>((route.query.spec_cluster_type as string) || ClusterTypes.TENDBSINGLE);
  const curChildTab = ref('');

  const renderTabs = computed(() =>
    tabs.filter((item) => {
      const data = funControllerStore.funControllerData[item.moduleId as ExtractedControllerDataKeys];
      return data && data.is_enabled;
    }),
  );

  const handleChangeClusterType = (value: string) => {
    if (curTab.value !== value) {
      curChildTab.value = '';
    }
  };
</script>
<style lang="less">
  .ticket-flow-list-page {
    .bk-tab-content {
      display: none;
    }

    .top-tabs {
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);
    }
  }
</style>
