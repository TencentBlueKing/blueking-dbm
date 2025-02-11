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
      :name="tab.id" />
  </BkTab>
</template>

<script setup lang="ts">
  import { useFunController } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  interface Props {
    exclude?: DBTypes[];
    labelConfig?: Record<DBTypes, string>;
  }

  interface TabItem {
    id: DBTypes;
    name: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    labelConfig: undefined,
    exclude: () => [],
  });

  const funControllerStore = useFunController();

  const moduleValue = defineModel<DBTypes>({
    default: DBTypes.MYSQL,
  });

  // 解决 labelConfig 变化后渲染样式异常问题
  const renderKey = ref(0);

  const renderTabs = computed(() =>
    Object.values(DBTypeInfos).reduce((result, item) => {
      const { id, name, moduleId } = item;
      const data = funControllerStore.funControllerData.getFlatData(moduleId);
      if (data[id] && !props.exclude.includes(id)) {
        result.push({
          id,
          name: props.labelConfig?.[id] || name,
        });
      }
      return result;
    }, [] as TabItem[]),
  );

  watch(
    () => [props.exclude, props.labelConfig],
    () => {
      renderKey.value += 1;
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
