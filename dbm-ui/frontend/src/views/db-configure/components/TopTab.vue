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
    class="db-configur-type-tab"
    type="unborder-card"
    @change="handleChange">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id" />
  </BkTab>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type {
    ControllerBaseInfo,
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { ClusterTypes } from '@common/const';

  interface TabItem {
    moduleId: ExtractedControllerDataKeys,
    id: FunctionKeys,
    name: string,
  }

  interface Emits {
    (e: 'change', value: string): void
  }

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const funControllerStore = useFunController();

  const tabs: TabItem[] = [{
    moduleId: 'mysql',
    id: ClusterTypes.TENDBSINGLE,
    name: t('MySQL单节点'),
  }, {
    moduleId: 'mysql',
    id: ClusterTypes.TENDBHA,
    name: t('MySQL主从'),
  }, {
    moduleId: 'redis',
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    name: t('TendisCache'),
  }, {
    moduleId: 'redis',
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    name: t('TendisSSD'),
  }, {
    moduleId: 'redis',
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    name: t('Tendisplus'),
  }, {
    moduleId: 'bigdata',
    id: ClusterTypes.ES,
    name: 'ES',
  }, {
    moduleId: 'bigdata',
    id: ClusterTypes.KAFKA,
    name: 'Kafka',
  }, {
    moduleId: 'bigdata',
    id: ClusterTypes.HDFS,
    name: 'HDFS',
  }, {
    moduleId: 'bigdata',
    id: ClusterTypes.INFLUXDB,
    name: 'InfluxDB',
  }, {
    moduleId: 'bigdata',
    id: ClusterTypes.PULSAE,
    name: 'Pulsar',
  }, {
    moduleId: 'mysql',
    id: ClusterTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
  }];

  const route = useRoute();
  const clusterType = computed(() => route.params.clusterType as string);
  const renderTabs = computed(() => tabs.filter((item) => {
    const data = funControllerStore.funControllerData[item.moduleId];
    return data
      && data.is_enabled
      && (data.children as Record<FunctionKeys, ControllerBaseInfo>)?.[item.id]?.is_enabled;
  }));
  const initActive = clusterType.value ?? renderTabs.value[0].id;
  const active = ref(initActive);

  handleChange(initActive);

  function handleChange(value: string) {
    emit('change', value);
  }
</script>
<style lang="less">
.db-configur-type-tab{
  background: #fff;
  box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

  .bk-tab-content{
    display: none;
  }
}
</style>
