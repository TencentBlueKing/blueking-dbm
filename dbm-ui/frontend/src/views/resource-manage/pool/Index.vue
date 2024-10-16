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
    v-model:active="activeTab"
    class="pool-tab"
    type="unborder-card"
    @change="handleChange">
    <BkTabPanel
      v-for="item in panels"
      :key="item.name"
      :label="item.label"
      :name="item.name" />
  </BkTab>
  <div class="pool-content">
    <KeepAlive>
      <Component :is="renderComponent" />
    </KeepAlive>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useDebouncedRef } from '@hooks';

  import HostList from './host-list/Index.vue';
  import SummaryView from './summary-view/Index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const panels = [
    {
      name: 'summary-view',
      label: t('统计视图'),
    },
    {
      name: 'host-list',
      label: t('主机列表'),
    },
  ];

  const activeTab = useDebouncedRef(route.params.page);

  const renderComponentMap = {
    'summary-view': SummaryView,
    'host-list': HostList,
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
      query: {},
    });
  };
</script>

<style lang="less" scoped>
  .pool-tab {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    :deep(.bk-tab-content) {
      display: none;
    }
  }

  .pool-content {
    padding: 24px;
  }
</style>
