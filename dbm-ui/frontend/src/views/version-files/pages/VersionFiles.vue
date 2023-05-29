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
      v-model:active="tabState.active"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of tabState.list"
        :key="tab.name"
        :label="tab.label"
        :name="tab.name" />
    </BkTab>
    <VersionFileContent
      :key="tabState.active"
      :info="activeTabInfo" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import VersionFileContent from './VersionFileContent.vue';

  const { t } = useI18n();

  const tabState = reactive({
    active: DBTypes.MYSQL,
    list: [{
      label: 'MySQL',
      name: DBTypes.MYSQL,
      children: [{
        label: 'MySQL',
        name: DBTypes.MYSQL,
      }, {
        label: 'MySQL-Proxy',
        name: 'mysql-proxy',
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }, {
        label: t('备份工具'),
        name: 'dbbackup',
      }, {
        label: t('校验工具'),
        name: 'mysql-checksum',
      }, {
        label: t('Binlog滚动备份工具'),
        name: 'rotate-binlog',
      }, {
        label: t('DBA工具集'),
        name: 'dba-toolkit',
      }, {
        label: t('MySQL监控'),
        name: 'mysql-monitor',
      }, {
        label: 'MySQL Crond',
        name: 'mysql-crond',
      }],
    }, {
      label: 'Redis',
      name: DBTypes.REDIS,
      children: [{
        label: 'Redis',
        name: DBTypes.REDIS,
      }, {
        label: 'TwemProxy',
        name: 'twemproxy',
      }, {
        label: 'Tendisplus',
        name: 'tendisplus',
      }, {
        label: 'TendisSSD',
        name: 'tendisssd',
      }, {
        label: 'Predixy',
        name: 'predixy',
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }, {
        label: t('工具包'),
        name: 'tools',
      }, {
        label: t('DB监控工具'),
        name: 'dbmon',
      }],
    }, {
      label: 'ES',
      name: DBTypes.ES,
      children: [{
        label: 'ES',
        name: DBTypes.ES,
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }],
    }, {
      label: 'Kafka',
      name: DBTypes.KAFKA,
      children: [{
        label: 'Kafka',
        name: DBTypes.KAFKA,
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }],
    }, {
      label: 'HDFS',
      name: DBTypes.HDFS,
      children: [{
        label: 'HDFS',
        name: DBTypes.HDFS,
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }],
    }, {
      label: 'Pulsar',
      name: DBTypes.PULSAR,
      children: [{
        label: 'Plusar',
        name: DBTypes.PULSAR,
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }],
    }, {
      label: 'InfluxDB',
      name: DBTypes.INFLUXDB,
      children: [{
        label: 'InfluxDB',
        name: DBTypes.INFLUXDB,
      }, {
        label: t('任务执行器'),
        name: 'actuator',
      }],
    }],
  });
  const activeTabInfo = computed(() => tabState.list.find(item => item.name === tabState.active)!);
</script>

<style lang="less" scoped>
  .version-files-view {
    height: 100%;
    padding-top: 42px;
  }
</style>
