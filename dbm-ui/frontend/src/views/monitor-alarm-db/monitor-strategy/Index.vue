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
  <div class="monitor-strategy-page">
    <BkTab
      v-model:active="activeTab"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of tabs"
        :key="tab.label"
        :label="tab.label"
        :name="tab.value" />
    </BkTab>
    <div class="monitor-strategy-content">
      <TypeContent :active-db-type="activeTab" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import TypeContent from './components/content/Index.vue';

  const { dbType } = useRoute().query as { dbType: string };

  const tabs = [
    {
      value: 'mysql',
      label: 'MySQL',
    },
    {
      value: 'tendbcluster',
      label: 'TenDBCluster',
    },
    {
      value: 'redis',
      label: 'Redis',
    },
    {
      value: 'mongodb',
      label: 'MongoDB',
    },
    {
      value: 'kafka',
      label: 'Kafka',
    },
    {
      value: 'hdfs',
      label: 'HDFS',
    },
    {
      value: 'es',
      label: 'ES',
    },
    {
      value: 'pulsar',
      label: 'Pulsar',
    },
    {
      value: 'influxdb',
      label: 'InfluxDB',
    },
    {
      value: 'riak',
      label: 'Riak',
    },
  ];

  const activeTab = ref(dbType ? dbType : tabs[0].value);

</script>
<style lang="less">
.monitor-strategy-page{
  .top-tabs{
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content{
      display: none;
    }
  }

  .monitor-strategy-content {
    height: calc(100vh - 150px);
    padding: 24px;
  }
}
</style>
