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
  <div class="configure-details">
    <MainBreadcrumbs class="custom-main-breadcrumbs" />
    <BkTab
      v-model:active="state.activeTab"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of tabs"
        :key="tab.name"
        v-bind="tab" />
    </BkTab>
    <div class="details-content">
      <template v-if="state.activeTab === 'publish'">
        <PublishRecord :fetch-params="publishFetchParams" />
      </template>
      <template v-else>
        <DetailsBase
          :data="state.data"
          :fetch-params="baseParams"
          :loading="state.loading"
          :sticky-top="92"
          @update-info="handleUpdateInfo" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getConfigBaseDetails } from '@services/configs';
  import type { ConfigBaseDetails } from '@services/types/configs';

  import { useMainViewStore } from '@stores';

  import { confLevelInfos, ConfLevels } from '@common/const';

  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  import DetailsBase from '../components/DetailsBase.vue';
  import PublishRecord from '../components/PublishRecord.vue';

  interface Props {
    clusterType: string,
    confType: string,
    version: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const state = reactive({
    loading: false,
    activeTab: '',
    data: {} as ConfigBaseDetails,
    // extraParametersCards: [] as ExtraConfListItem[]
  });
  const baseParams = computed(() => ({
    meta_cluster_type: props.clusterType,
    conf_type: props.confType,
    version: props.version,
  }));
  const publishFetchParams = computed(() => ({
    ...baseParams.value,
    level_name: ConfLevels.PLAT,
    level_value: 0,
    bk_biz_id: 0,
  }));
  // 顶部 tabs
  const tabs = reactive([{
    label: t('基础信息'),
    name: 'base',
  }, {
    label: t('发布记录'),
    name: 'publish',
  }]);

  /**
   * 设置自定义面包屑
   */
  const mainViewStore = useMainViewStore();
  nextTick(() => {
    mainViewStore.$patch({
      customBreadcrumbs: true,
      hasPadding: false,
    });
  });
  watch(() => state.data, () => {
    mainViewStore.breadCrumbsTitle = state.data.name;
    mainViewStore.tags = [{
      theme: '',
      text: state.data.version,
    }, {
      theme: 'info',
      text: confLevelInfos[ConfLevels.PLAT].tagText,
    }];
  }, { deep: true });


  /**
   * 获取集群通用默认配置 - dbconf
   */
  getDefaultConfig();
  function getDefaultConfig() {
    state.loading = true;
    getConfigBaseDetails(baseParams.value)
      .then((res) => {
        state.data = res;
      })
      .finally(() => {
        state.loading = false;
      });
  }

  // 更新基础信息
  function handleUpdateInfo({ key, value }: { key: string, value: string }) {
    Object.assign(state.data, { [key]: value });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .configure-details {
    height: 100%;
  }

  .operations {
    .flex-center();

    &__button {
      width: 76px;
      margin-left: 8px;
      font-size: @font-size-mini;
    }
  }

  .details-content {
    height: 100%;
    padding: 118px 24px 24px;
  }
</style>
