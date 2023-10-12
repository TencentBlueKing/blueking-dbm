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
  <div class="main-content">
    <BkLoading
      :loading="state.loading"
      style="height: 100%;"
      :z-index="12">
      <ConfigEmpty v-if="showEmpty" />
      <BkTab
        v-else
        v-model:active="activatedTab"
        type="unborder-card">
        <BkTabPanel
          v-for="tab of tabs"
          :key="tab.name"
          v-bind="tab"
          render-directive="if">
          <ConfigDetails
            :data="state.data"
            :fetch-params="fetchParams"
            :loading="state.loadingDetails" />
        </BkTabPanel>
      </BkTab>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import ConfigEmpty from '../ConfigEmpty.vue';
  import { useBaseDetails } from '../hooks/useBaseDetails';

  import ConfigDetails from './ConfigDetails.vue';

  const { t } = useI18n();

  /**
   * 顶部 tabs
   */
  const activatedTab = ref('base');
  const tabs = reactive([{
    label: t('参数管理'),
    name: 'base',
  }]);

  const { state, fetchParams, dbType } = useBaseDetails();
  const showEmpty = computed(() => state.isEmpty && dbType.value === DBTypes.MYSQL);
</script>

<style lang="less" scoped>
  @import "@styles/common.less";

  .main-content {
    height: calc(100% - 42px);

    :deep(.db-card) {
      box-shadow: none;
    }

    .bk-tab {
      height: 100%;

      :deep(.bk-tab-content) {
        &:extend(.db-scroll-y);

        height: calc(100% - 42px);
        padding-bottom: 0;
      }
    }
  }
</style>
