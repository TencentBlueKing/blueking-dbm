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
    <ClusterTab
      v-model="curTab"
      :excludes="[ClusterTypes.SQLSERVER_SINGLE]" />
    <div
      :key="curTab"
      class="wrapper">
      <BkTab
        v-model:active="curChildTab"
        type="card">
        <BkTabPanel
          v-for="childTab of childrenTabs"
          :key="childTab.id"
          :label="childTab.name"
          :name="childTab.id" />
      </BkTab>
      <SpecList
        :cluster-type="curTab"
        :cluster-type-label="clusterTypeLabel"
        :machine-type="curChildTab"
        :machine-type-label="machineTypeLabel" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { ControllerBaseInfo } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import ClusterTab from '@components/cluster-tab/Index.vue';

  import SpecList from './components/SpecList.vue';

  const route = useRoute();
  const funControllerStore = useFunController();

  const curTab = ref<ClusterTypes>(ClusterTypes.TENDBSINGLE);
  const curChildTab = ref('');

  const renderTabs = computed(() =>
    Object.values(clusterTypeInfos).filter((item) => {
      const data = funControllerStore.funControllerData[item.moduleId];
      if (!data) {
        return false;
      }

      const childItem = (data.children as Record<ClusterTypes, ControllerBaseInfo>)[item.id];

      // 若有对应的模块子功能，判断是否开启
      if (childItem) {
        return data && data.is_enabled && childItem.is_enabled;
      }

      // 若无，则判断整个模块是否开启
      return data && data.is_enabled;
    }),
  );
  const childrenTabs = computed(() => renderTabs.value.find((item) => item.id === curTab.value)?.machineList || []);
  const clusterTypeLabel = computed(() => renderTabs.value.find((item) => item.id === curTab.value)?.name ?? '');
  const machineTypeLabel = computed(() => childrenTabs.value.find((item) => item.id === curChildTab.value)?.name ?? '');

  watch(curTab, (newVal, oldVal) => {
    if (oldVal !== newVal) {
      curChildTab.value = '';
    }
  });

  onMounted(() => {
    const { spec_cluster_type: clusterType } = route.query;
    if (clusterType) {
      curTab.value = clusterType as ClusterTypes;
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
