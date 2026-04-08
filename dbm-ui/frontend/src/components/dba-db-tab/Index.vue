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
    class="db-tab"
    type="unborder-card">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id">
      <template #label>
        {{ tab.name }}
        <span v-if="countConfig"> ({{ countConfig?.[tab.id] || 0 }}) </span>
      </template>
    </BkTabPanel>
  </BkTab>
</template>

<script setup lang="ts">
  import { useUserDbaComponents } from '@hooks';

  import { DBTypeInfos } from '@common/const';

  interface Props {
    countConfig?: Record<string, number>;
  }

  const props = withDefaults(defineProps<Props>(), {
    countConfig: () => ({}) as NonNullable<Props['countConfig']>,
  });

  const moduleValue = defineModel<string>({
    default: '',
  });

  const { components: dbaComponents, loading } = useUserDbaComponents();

  defineExpose({ loading });

  const dbaDbTypeMap = computed(
    () => new Map(dbaComponents.value.map((item) => [item.db_type, item.db_type_display])),
  );

  const renderTabs = computed(() =>
    Object.values(DBTypeInfos)
      .filter((item) => dbaDbTypeMap.value.has(item.id))
      .map((item) => ({
        id: item.id,
        name: dbaDbTypeMap.value.get(item.id) || item.name,
      })),
  );

  // 接口返回后，如果当前 modelValue 不在列表中，自动选中第一个
  watch(
    renderTabs,
    (tabs) => {
      if (tabs.length > 0 && !tabs.some((tab) => tab.id === moduleValue.value)) {
        moduleValue.value = tabs[0].id;
      }
    },
    { immediate: true },
  );

  // 如果有 countConfig，自动选中第一个非 0 的 tab
  watch(
    () => props.countConfig,
    () => {
      const activeTab = Object.keys(props.countConfig).find((key) => props.countConfig[key] > 0) || '';
      if (activeTab) {
        moduleValue.value = activeTab;
      }
    },
    { immediate: true },
  );
</script>

<style lang="less">
  .db-tab {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content {
      display: none;
    }
  }
</style>
