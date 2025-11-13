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
  <div>
    <BkTab
      v-model:active="activeTab"
      class="pool-tab"
      type="unborder-card"
      @change="handleChange">
      <BkTabPanel
        v-for="item in renderPanels"
        :key="item.name"
        :label="item.label"
        :name="item.name" />
    </BkTab>
    <div class="pool-content">
      <KeepAlive>
        <Component :is="renderComponent" />
      </KeepAlive>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useDebouncedRef } from '@hooks';

  import { useFunController } from '@stores';

  import Flow from './components/flow/Index.vue';
  import Replenish from './components/replenish/Index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const funControllerStore = useFunController();

  const panels = [
    {
      label: t('资源流转记录'),
      name: 'flow',
    },
    {
      label: t('资源补货记录'),
      name: 'replenish',
    },
  ];

  const renderPanels = computed(() =>
    panels.filter((item) => {
      const data = funControllerStore.funControllerData.resourceManage.children.resourceOperationRecord;
      if (!data) {
        return false;
      }

      const childItem = data.children[item.name];

      // 若有对应的模块子功能，判断是否开启
      if (childItem) {
        return data && data.is_enabled && childItem.is_enabled;
      }

      // 若无，则判断整个模块是否开启
      return data && data.is_enabled;
    }),
  );

  const activeTab = useDebouncedRef(route.params.page as string);

  const renderComponentMap = {
    flow: Flow,
    replenish: Replenish,
  };

  const renderComponent = computed(() => renderComponentMap[activeTab.value as keyof typeof renderComponentMap]);

  watch(
    () => route.params,
    () => {
      activeTab.value = route.params.page as string;
    },
  );

  const handleChange = (value: string) => {
    router.replace({
      params: {
        page: value,
      },
    });
  };
</script>

<style lang="less" scoped>
  .pool-tab {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    :deep(.bk-tab-header-active-bar) {
      transition: none;
    }

    :deep(.bk-tab-content) {
      display: none;
    }
  }

  .pool-content {
    padding: 24px;
  }
</style>
