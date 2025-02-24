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
    <DbTab v-model="tabActive" />
    <FileContent
      :key="tabActive"
      :info="activeTabInfo"
      :pkg-type-list="pkgList" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';
  import { listPackageTypes } from '@services/source/package';

  import { useFunController } from '@stores';

  import { DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import FileContent from './components/FileContent.vue';

  interface TabItem {
    children: {
      controllerId?: FunctionKeys;
      label: string;
      name: string;
    }[];
    controller: {
      id?: FunctionKeys;
      moduleId: ExtractedControllerDataKeys;
    };
    label: string;
    name: string;
  }

  const { t } = useI18n();
  const funControllerStore = useFunController();

  const tabs: TabItem[] = [
    {
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
          label: t('备份工具-TXSQL'),
          name: 'dbbackup-txsql',
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
        {
          label: 'tbinlogdumper',
          name: 'tbinlogdumper',
        },
      ],
      controller: {
        moduleId: 'mysql',
      },
      label: 'MySQL',
      name: DBTypes.MYSQL,
    },
    {
      children: [
        {
          label: 'TenDBCluster',
          name: DBTypes.TENDBCLUSTER,
        },
      ],
      controller: {
        moduleId: 'mysql',
      },
      label: 'TenDBCluster',
      name: DBTypes.TENDBCLUSTER,
    },
    {
      children: [
        {
          label: 'Redis',
          name: DBTypes.REDIS,
        },
        {
          controllerId: 'TwemproxyRedisInstance',
          label: 'TwemProxy',
          name: 'twemproxy',
        },
        {
          controllerId: 'PredixyTendisplusCluster',
          label: 'Tendisplus',
          name: 'tendisplus',
        },
        {
          controllerId: 'TwemproxyTendisSSDInstance',
          label: 'TendisSSD',
          name: 'tendisssd',
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
        {
          label: 'RedisModules',
          name: 'redis-modules',
        },
      ],
      controller: {
        moduleId: 'redis',
      },
      label: 'Redis',
      name: DBTypes.REDIS,
    },
    {
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
      controller: {
        id: 'es',
        moduleId: 'bigdata',
      },
      label: 'ES',
      name: DBTypes.ES,
    },
    {
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
      controller: {
        id: 'kafka',
        moduleId: 'bigdata',
      },
      label: 'Kafka',
      name: DBTypes.KAFKA,
    },
    {
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
      controller: {
        id: 'hdfs',
        moduleId: 'bigdata',
      },
      label: 'HDFS',
      name: DBTypes.HDFS,
    },
    {
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
      controller: {
        id: 'pulsar',
        moduleId: 'bigdata',
      },
      label: 'Pulsar',
      name: DBTypes.PULSAR,
    },
    {
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
      controller: {
        id: 'influxdb',
        moduleId: 'bigdata',
      },
      label: 'InfluxDB',
      name: DBTypes.INFLUXDB,
    },
    {
      children: [
        {
          label: 'Riak',
          name: DBTypes.RIAK,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
        {
          label: t('Riak监控'),
          name: 'riak-monitor',
        },
      ],
      controller: {
        id: 'riak',
        moduleId: 'bigdata',
      },
      label: 'Riak',
      name: DBTypes.RIAK,
    },
    {
      children: [
        {
          label: 'MongoDB',
          name: DBTypes.MONGODB,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
        {
          label: t('DB监控工具'),
          name: 'dbmon',
        },
        {
          label: t('工具包'),
          name: 'dbtools',
        },
        {
          label: t('工具集'),
          name: 'mongo-toolkit',
        },
      ],
      controller: {
        moduleId: 'mongodb',
      },
      label: 'MongoDB',
      name: DBTypes.MONGODB,
    },
    {
      children: [
        {
          label: 'SQLServer',
          name: DBTypes.SQLSERVER,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
      controller: {
        moduleId: 'sqlserver',
      },
      label: 'SQLServer',
      name: DBTypes.SQLSERVER,
    },
    {
      children: [
        {
          label: 'Doris',
          name: DBTypes.DORIS,
        },
        {
          label: t('任务执行器'),
          name: 'actuator',
        },
      ],
      controller: {
        id: 'doris',
        moduleId: 'bigdata',
      },
      label: 'Doris',
      name: DBTypes.DORIS,
    },
  ];

  const renderTabs = tabs.filter((item) => {
    const { id, moduleId } = item.controller;
    const data = funControllerStore.funControllerData[moduleId];
    // 整个模块没有开启
    if (!data || data.is_enabled !== true) {
      return false;
    }
    const children = data.children as Record<FunctionKeys, ControllerBaseInfo>;
    // 模块中的功能没开启
    if (id && !children[id]?.is_enabled) {
      return false;
    }

    // 处理 tab.children
    const tabChildren = item.children.filter((child) => {
      // 不需要校验功能是否开启
      if (child.controllerId === undefined) {
        return true;
      }

      return children[child.controllerId].is_enabled;
    });
    Object.assign(item, {
      children: tabChildren,
    });

    return true;
  });

  const tabActive = ref<DBTypes>(DBTypes.MYSQL);
  const packageTypeMap = ref<Record<string, string[]>>({});
  const activeTabInfo = computed(() => {
    const tabList = renderTabs.find((item) => item.name === tabActive.value);
    return tabList
      ? tabList
      : {
          label: '',
          name: '',
        };
  });

  const pkgList = computed(() => packageTypeMap.value![tabActive.value] ?? []);

  useRequest(listPackageTypes, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
      },
    ],
    onSuccess(data) {
      packageTypeMap.value = data;
    },
  });
</script>
<style lang="less">
  .version-files-view {
    .top-tabs {
      padding: 0 24px;
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content {
        display: none;
      }
    }
  }
</style>
