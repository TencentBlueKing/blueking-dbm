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
  <div class="config-biz-details">
    <MainBreadcrumbs>
      <template #append>
        <div class="operations" />
      </template>
    </MainBreadcrumbs>
    <BkTab
      v-model:active="state.activeTab"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of tabs"
        :key="tab.name"
        v-bind="tab" />
    </BkTab>
    <div class="details-content db-scroll-y">
      <template v-if="state.activeTab === 'publish'">
        <PublishRecord :fetch-params="fetchParams" />
      </template>
      <template v-else>
        <DetailsBase
          :data="state.data"
          :fetch-params="fetchParams"
          :level="ConfLevels.APP"
          :loading="state.loading"
          :sticky-top="-26"
          @update-info="handleUpdateInfo" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/configs';
  import type {
    ConfigBaseDetails,
    GetLevelConfigParams,
  } from '@services/types/configs';

  import { useMainViewStore } from '@stores';

  import { confLevelInfos, ConfLevels } from '@common/const';

  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';

  import DetailsBase from '@views/db-configure/components/DetailsBase.vue';
  import PublishRecord from '@views/db-configure/components/PublishRecord.vue';
  import { useLevelParams } from '@views/db-configure/hooks/useLevelParams';

  interface Props {
    clusterType: string,
    confType: string,
    version: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const state = reactive({
    loading: false,
    activeTab: 'base',
    data: {} as ConfigBaseDetails,
  });

  // 获取业务层级相关参数
  const levelParams = useLevelParams(false);
  const fetchParams = computed(() => ({
    meta_cluster_type: props.clusterType,
    conf_type: props.confType,
    version: props.version,
    ...levelParams.value,
  }));

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
      text: confLevelInfos[ConfLevels.APP].tagText,
    }];
  }, { deep: true });

  /**
   * 顶部 tabs
   */
  const tabs = reactive([{
    label: t('基础信息'),
    name: 'base',
  }, {
    label: t('发布记录'),
    name: 'publish',
  }]);

  /**
   * 查询配置详情
   */
  const fetchLevelConfig = () => {
    state.loading = true;
    getLevelConfig(fetchParams.value as GetLevelConfigParams)
      .then((res) => {
        state.data = res;
      })
      .finally(() => {
        state.loading = false;
      });
  };
  fetchLevelConfig();

  // 更新基础信息
  function handleUpdateInfo({ key, value }: { key: string, value: string }) {
    Object.assign(state.data, { [key]: value });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .config-biz-details {
    height: 100%;

    :deep(.base-card) {
      margin-bottom: 16px;
    }
  }

  .operations {
    .flex-center();

    &__button {
      width: 76px;
      margin-left: 8px;
      font-size: @font-size-mini;
    }

    &__more {
      display: block;
      width: 26px;
      margin-left: 8px;
      font-size: @font-size-large;
      line-height: 26px;
      cursor: pointer;
      border-radius: 2px;

      &:hover {
        background-color: @bg-dark-gray;
      }
    }
  }

  .details-content {
    height: calc(100% - 52px);
    padding: 66px 24px 24px;

    :deep(.details-base) {
      height: 100%;
    }
  }
</style>
