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
    v-model:active="active"
    class="top-tabs"
    type="unborder-card"
    @change="handleChange">
    <BkTabPanel
      v-for="tab of tabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id" />
  </BkTab>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  const emit = defineEmits(['change']);

  const { t } = useI18n();

  const tabs = [{
    id: ClusterTypes.TENDBSINGLE,
    name: t('MySQL单节点'),
  }, {
    id: ClusterTypes.TENDBHA,
    name: t('MySQL高可用'),
  }, {
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    name: t('TendisCache集群'),
  }, {
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    name: t('TendisSSD存储版集群'),
  }, {
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    name: t('Tendisplus存储版集群'),
  }, {
    id: ClusterTypes.ES,
    name: 'ES',
  }, {
    id: ClusterTypes.KAFKA,
    name: 'Kafka',
  }, {
    id: ClusterTypes.HDFS,
    name: 'HDFS',
  }, {
    id: ClusterTypes.INFLUXDB,
    name: 'InfluxDB',
  }, {
    id: ClusterTypes.PULSAE,
    name: 'Pulsar',
  }];

  const route = useRoute();
  const clusterType = computed(() => route.params.clusterType as string);
  const initActive = clusterType.value ?? tabs[0].id;
  const active = ref(initActive);

  handleChange(initActive);

  function handleChange(value: string) {
    emit('change', value);
  }
</script>
