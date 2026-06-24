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
    :type="type">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id" />
  </BkTab>
</template>

<script setup lang="ts">
  import BkTab from 'bkui-vue/lib/tab';
  import { type ComponentProps } from 'vue-component-type-helpers';

  import { useFunController, useUserProfile } from '@stores';

  import { DBTypeInfos, DBTypes, UserPersonalSettings } from '@common/const';

  interface Props {
    exclude?: DBTypes[];
    labelConfig?: Record<DBTypes, string>;
    suffixItems?: TabItem[];
    topSort?: boolean;
    type?: ComponentProps<typeof BkTab>['type'];
  }

  interface TabItem {
    id: string;
    name: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    exclude: () => [],
    labelConfig: undefined,
    suffixItems: () => [],
    type: 'unborder-card',
  });

  const moduleValue = defineModel<DBTypes>();

  const funControllerStore = useFunController();
  const userProfileStore = useUserProfile();

  // 解决 labelConfig 变化后渲染样式异常问题
  const renderKey = ref(0);

  const renderTabs = computed(() => {
    const renderList = Object.values(DBTypeInfos).reduce((result, item) => {
      const { id, moduleId, name } = item;
      const data = funControllerStore.funControllerData.getFlatData(moduleId);
      if (data[id] && !props.exclude.includes(id)) {
        result.push({
          id,
          name: props.labelConfig?.[id] || name,
        });
      }
      return result;
    }, [] as TabItem[]);

    if (props.topSort) {
      const renderMap = Object.fromEntries(renderList.map((item) => [item.id, item]));
      const topDbTypes: string[] = (
        (userProfileStore.profile[UserPersonalSettings.TOP_DB_TYPES] || []) as string[]
      ).filter((item) => renderMap[item]);

      if (topDbTypes.length > 0) {
        const topDbTypeMap = Object.fromEntries(topDbTypes.map((item) => [item, renderMap[item]]));
        const topList = topDbTypes.map((topItem) => renderMap[topItem as DBTypes]);
        const commonList = renderList.filter((item) => !topDbTypeMap[item.id]);
        return topList.concat(commonList).concat(props.suffixItems);
      }
    }

    return renderList.concat(props.suffixItems);
  });

  watch(
    () => [props.exclude, props.labelConfig],
    () => {
      renderKey.value += 1;
    },
    {
      immediate: true,
    },
  );
  watch(
    renderTabs,
    () => {
      if (!moduleValue.value && renderTabs.value.length > 0) {
        moduleValue.value = renderTabs.value[0].id;
      }
    },
    {
      immediate: true,
    },
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
