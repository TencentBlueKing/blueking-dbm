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
  <div class="module-content">
    <BkLoading
      :loading="state.loading"
      style="height: 100%;"
      :z-index="12">
      <ConfigEmpty v-if="state.isEmpty" />
      <BkTab
        v-else
        v-model:active="activatedTab"
        type="unborder-card">
        <BkTabPanel
          v-for="tab of tabs"
          :key="tab.name"
          v-bind="tab"
          render-directive="if">
          <template v-if="tab.name === 'publish' && publishParams !== null">
            <PublishRecord :fetch-params="publishParams" />
          </template>
          <template v-if="tab.name !== 'publish' && configParams !== null">
            <ConfigDetails
              :data="state.data"
              :fetch-params="configParams"
              :loading="state.loadingDetails" />
          </template>
        </BkTabPanel>
      </BkTab>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { GetLevelConfigParams, PlatConfDetailsParams } from '@services/types/configs';

  import PublishRecord from '../../components/PublishRecord.vue';
  import ConfigEmpty from '../components/ConfigEmpty.vue';
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
  }, {
    label: t('发布记录'),
    name: 'publish',
  }]);

  const { state, fetchParams } = useBaseDetails();
  const publishParams = computed(() => {
    if (fetchParams.value) {
      const {
        meta_cluster_type,
        conf_type,
        version,
        bk_biz_id,
        level_name,
        level_value,
      } = fetchParams.value;
      return {
        meta_cluster_type,
        conf_type,
        version: version ? version : '',
        bk_biz_id,
        level_name,
        level_value: String(level_value),
      };
    }
    return null;
  });
  const configParams = computed(() => {
    if (fetchParams.value) {
      const {
        meta_cluster_type,
        conf_type,
        version,
        bk_biz_id,
        level_name,
        level_value,
      } = fetchParams.value;
      return {
        meta_cluster_type,
        conf_type,
        version,
        bk_biz_id,
        level_name,
        level_value,
      } as PlatConfDetailsParams | GetLevelConfigParams;
    }
    return null;
  });
</script>

<style lang="less" scoped>
  @import "@styles/common.less";

  .module-content {
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
