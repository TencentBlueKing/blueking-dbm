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
  <div class="version-files-view">
    <BkTab
      v-model:active="tabActive"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of renderTabs"
        :key="tab.name"
        :label="tab.label"
        :name="tab.name" />
    </BkTab>
    <FileContent
      :key="tabActive"
      :info="activeTabInfo" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';

  import {
    useFunController,
    useMainViewStore,
  } from '@stores';

  import { DBTypes } from '@common/const';

  import FileContent from './components/FileContent.vue';

  interface TabItem {
    controller: {
      moduleId: ExtractedControllerDataKeys,
      id?: FunctionKeys
    },
    label: string,
    name: string,
    children: {
      label: string,
      name: string,
      controllerId?: FunctionKeys
    }[]
  }

  const { t } = useI18n();
  const funControllerStore = useFunController();
  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;

  const tabs: TabItem[] = [
    {
      controller: {
        moduleId: 'mysql',
      },
      label: 'MySQL',
      name: DBTypes.MYSQL,
      children: [
        {
          label: 'MySQL',
          name: DBTypes.MYSQL,
        },
        {
          label: 'MySQL-Proxy',
          name: 'mysql-proxy',
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
        {
          label: t('备份工具'),
          name: 'dbbackup',
        },
        {
          label: t('校验工具'),
          name: 'mysql-checksum',
        },
        {
          label: t('Binlog滚动备份工具'),
          name: 'rotate-binlog',
        },
        {
          label: t('DBA工具集'),
          name: 'dba-toolkit',
        },
        {
          label: t('MySQL监控'),
          name: 'mysql-monitor',
        },
        {
          label: 'MySQL Crond',
          name: 'mysql-crond',
        },
        {
          label: 'Spider',
          name: 'spider',
        },
        {
          label: 'TDBCTL',
          name: 'tdbctl',
        },
      ],
    },
    {
      controller: {
        moduleId: 'redis',
      },
      label: 'Redis',
      name: DBTypes.REDIS,
      children: [
        {
          label: 'Redis',
          name: DBTypes.REDIS,
        },
        {
          label: 'TwemProxy',
          name: 'twemproxy',
          controllerId: 'TwemproxyRedisInstance',
        },
        {
          label: 'Tendisplus',
          name: 'tendisplus',
          controllerId: 'PredixyTendisplusCluster',
        },
        {
          label: 'TendisSSD',
          name: 'tendisssd',
          controllerId: 'TwemproxyTendisSSDInstance',
        },
        {
          label: 'Predixy',
          name: 'predixy',
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
        {
          label: t('工具包'),
          name: 'tools',
        },
        {
          label: t('DB监控工具'),
          name: 'dbmon',
        },
        {
          label: 'RedisDTS',
          name: 'redis-dts',
        },
      ],
    },
    {
      controller: {
        moduleId: 'bigdata',
        id: 'es',
      },
      label: 'ES',
      name: DBTypes.ES,
      children: [
        {
          label: 'ES',
          name: DBTypes.ES,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
    },
    {
      controller: {
        moduleId: 'bigdata',
        id: 'kafka',
      },
      label: 'Kafka',
      name: DBTypes.KAFKA,
      children: [
        {
          label: 'Kafka',
          name: DBTypes.KAFKA,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
    },
    {
      controller: {
        moduleId: 'bigdata',
        id: 'hdfs',
      },
      label: 'HDFS',
      name: DBTypes.HDFS,
      children: [
        {
          label: 'HDFS',
          name: DBTypes.HDFS,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
    },
    {
      controller: {
        moduleId: 'bigdata',
        id: 'pulsar',
      },
      label: 'Pulsar',
      name: DBTypes.PULSAR,
      children: [
        {
          label: 'Plusar',
          name: DBTypes.PULSAR,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
    },
    {
      controller: {
        moduleId: 'bigdata',
        id: 'influxdb',
      },
      label: 'InfluxDB',
      name: DBTypes.INFLUXDB,
      children: [
        {
          label: 'InfluxDB',
          name: DBTypes.INFLUXDB,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
    },
  ];

  const renderTabs = computed(() => tabs.filter((item) => {
    const { moduleId, id } = item.controller;
    const data = funControllerStore.funControllerData[moduleId];
    // 整个模块没有开启
    if (data.is_enabled !== true) return false;
    const children = (data.children as Record<FunctionKeys, ControllerBaseInfo>);
    // 模块中的功能没开启
    if (id && children[id].is_enabled !== true) {
      return false;
    }

    // 处理 tab.children
    const tabChildren = item.children.filter((child) => {
      // 不需要校验功能是否开启
      if (child.controllerId === undefined) return true;

      return children[child.controllerId].is_enabled;
    });
    Object.assign(item, {
      children: tabChildren,
    });

    return true;
  }));
  const tabActive = ref(renderTabs.value[0].name);

  const activeTabInfo = computed(() => {
    const tabList = renderTabs.value.find(item => item.name === tabActive.value);
    return tabList ? tabList : {
      label: '',
      name: '',
    };
  });
</script>
<style lang="less">
  .version-files-view {
    .top-tabs{
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content{
        display: none;
      }
    }
  }
</style>
