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
    :key="renderKey"
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

  import { DBTypes } from '@common/const';

  interface Props {
    // tab 标签的计数配置
    countConfig?: Record<string, number>;
    // 只展示指定的 dbType
    include?: DBTypes[];
  }

  const props = withDefaults(defineProps<Props>(), {
    countConfig: () => ({}) as NonNullable<Props['countConfig']>,
    include: () => [] as NonNullable<Props['include']>,
  });

  const moduleValue = defineModel<string>({
    default: '',
  });

  const { components: dbaComponents, loading } = useUserDbaComponents();

  defineExpose({ loading });

  // Tab 列表变化时重新渲染，避免样式异常
  const renderKey = ref(0);

  const includeSet = computed(() => new Set<string>(props.include));

  const renderTabs = computed(() =>
    dbaComponents.value
      .filter((item) => includeSet.value.has(item.db_type))
      .map((item) => ({
        id: item.db_type,
        name: item.db_type_display,
      })),
  );

  // Tab 列表变化时递增 renderKey 重新渲染，并自动选中合适的 Tab
  watch(
    renderTabs,
    (tabs) => {
      renderKey.value += 1;
      if (tabs.length > 0 && !tabs.some((tab) => tab.id === moduleValue.value)) {
        nextTick(() => {
          moduleValue.value = tabs[0].id;
        });
      }
    },
    { immediate: true },
  );

  // 如果有 countConfig，自动选中第一个非 0 的 tab
  watch(
    () => props.countConfig,
    (countConfig) => {
      const activeTab = Object.keys(countConfig).find((key) => countConfig[key] > 0);
      if (activeTab) {
        nextTick(() => {
          moduleValue.value = activeTab;
        });
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
