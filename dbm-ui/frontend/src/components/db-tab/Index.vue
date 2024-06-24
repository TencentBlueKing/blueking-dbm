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
  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { DBTypes } from '@common/const';

  interface TabItem {
    moduleId: ExtractedControllerDataKeys;
    label: string;
    name: DBTypes;
  }
  const tabs: TabItem[] = [
    {
      moduleId: 'mysql',
      label: 'MySQL',
      name: DBTypes.MYSQL,
    },
    {
      moduleId: 'redis',
      label: 'Redis',
      name: DBTypes.REDIS,
    },
    {
      moduleId: 'mongodb',
      label: 'MongoDB',
      name: DBTypes.MONGODB,
    },
    {
      moduleId: 'sqlserver',
      label: 'SQLServer',
      name: DBTypes.SQLSERVER,
    },
    {
      moduleId: 'bigdata',
      label: 'Kafka',
      name: DBTypes.KAFKA,
    },
    {
      moduleId: 'bigdata',
      label: 'HDFS',
      name: DBTypes.HDFS,
    },
    {
      moduleId: 'bigdata',
      label: 'ES',
      name: DBTypes.ES,
    },
    {
      moduleId: 'bigdata',
      label: 'Pulsar',
      name: DBTypes.PULSAR,
    },
    {
      moduleId: 'bigdata',
      label: 'InfluxDB',
      name: DBTypes.INFLUXDB,
    },
    {
      moduleId: 'bigdata',
      label: 'Spider',
      name: DBTypes.SPIDER,
    },
    {
      moduleId: 'bigdata',
      label: 'Riak',
      name: DBTypes.RIAK,
    },
  ];

  const funControllerStore = useFunController();

  const moduleValue = defineModel<DBTypes>({
    default: DBTypes.MYSQL,
  });

  const renderTabs = tabs.filter((item) => {
    const { moduleId, name: dbType } = item;
    const data = funControllerStore.funControllerData[moduleId];
    // 整个模块没有开启
    if (!data || data.is_enabled !== true) {
      return false;
    }
    if (dbType === item.moduleId && data.is_enabled) {
      return true;
    }
    const children = data.children as Record<DBTypes, ControllerBaseInfo>;
    return children[dbType] && children[dbType]?.is_enabled;
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
