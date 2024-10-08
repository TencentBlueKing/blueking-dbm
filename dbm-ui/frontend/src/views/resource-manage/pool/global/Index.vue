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
    <Teleport to="#dbContentTitleAppend">
      <BkTag
        class="ml-8 mr-8"
        theme="info">
        {{ t('全局') }}
      </BkTag>
      <ImportHostBtn
        class="w-88"
        @export-host="handleImportHost" />
    </Teleport>
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
      <ImportHost v-model:is-show="isShowImportHost" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useDebouncedRef } from '@hooks';

  import ImportHost from '../components/host-list/components/import-host/Index.vue';
  import ImportHostBtn from '../components/host-list/components/ImportHostBtn.vue';
  import HostList from '../components/host-list/Index.vue';
  import SummaryView from '../components/summary-view/Index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const isShowImportHost = ref(false);

  const panels = [
    {
      name: 'host-list',
      label: t('主机列表'),
    },
    {
      name: 'summary-view',
      label: t('统计视图'),
    },
  ];

  const activeTab = useDebouncedRef(route.params.page as string);

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
    });
  };

  // 导入主机
  const handleImportHost = () => {
    isShowImportHost.value = true;
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
