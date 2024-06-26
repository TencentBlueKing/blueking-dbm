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
    class="cluster-tab"
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

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  interface TabItem {
    label: string;
    name: ClusterTypes;
  }

  const funControllerStore = useFunController();

  const moduleValue = defineModel<ClusterTypes>({
    default: ClusterTypes.TENDBSINGLE,
  });

  const renderTabs = Object.values(clusterTypeInfos).reduce((result, item) => {
    const { id: clusterType, name, dbType, moduleId } = item;
    const realModuleId = moduleId ?? (dbType as ExtractedControllerDataKeys);
    const data = funControllerStore.funControllerData[realModuleId];
    if (dbType === moduleId && data?.is_enabled) {
      result.push({
        label: name,
        name: clusterType,
      });
    } else {
      const children = data?.children as Record<ClusterTypes, ControllerBaseInfo>;
      if (children[clusterType]?.is_enabled) {
        result.push({
          label: name,
          name: clusterType,
        });
      }
    }
    return result;
  }, [] as TabItem[]);
</script>

<style lang="less">
  .cluster-tab {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content {
      display: none;
    }
  }
</style>
