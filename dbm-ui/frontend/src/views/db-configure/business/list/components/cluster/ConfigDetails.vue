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
  <div class="config-details">
    <BkLoading
      :loading="loading"
      style="height: 100%;"
      :z-index="12">
      <div class="config-details__operations" />
      <DetailsBase
        class="config-details__content"
        :data="props.data"
        :extra-parameters-cards="state.extraParametersCards"
        :fetch-params="props.fetchParams"
        :level="ConfLevels.CLUSTER"
        :loading="false"
        :route-params="routeParams"
        :sticky-top="-16"
        :title="title"
        @update-info="handleUpdateInfo" />
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/configs';
  import type {
    ConfigBaseDetails,
    GetLevelConfigParams,
    ParameterConfigItem,
    PlatConfDetailsParams,
    PlatConfDetailsUpdateParams,
  } from '@services/types/configs';

  import {
    type ClusterTypesValues,
    ConfLevels,
  } from '@common/const';

  import {
    defaultConfTitles,
    extraParamertesCluster,
  } from '@views/db-configure/common/const';
  import type { ExtraConfListItem } from '@views/db-configure/common/types';
  import DetailsBase from '@views/db-configure/components/DetailsBase.vue';

  import { useBaseDetails } from '../hooks/useBaseDetails';

  interface Props {
    data?: ConfigBaseDetails,
    loading?: boolean,
    fetchParams?: PlatConfDetailsUpdateParams | PlatConfDetailsParams
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({
      conf_items: [] as ParameterConfigItem[],
    } as ConfigBaseDetails),
    loading: false,
    fetchParams: () => ({} as PlatConfDetailsUpdateParams),
  });

  const { t } = useI18n();
  const route = useRoute();
  const state = reactive<{
    extraParametersCards: ExtraConfListItem[]
  }>({
    extraParametersCards: [],
  });
  const title = computed(() => defaultConfTitles[props.fetchParams.meta_cluster_type as ClusterTypesValues] || t('参数配置'));
  const { getFetchParams } = useBaseDetails(false);

  // 编辑路由参数
  const routeParams = computed(() => ({
    clusterType: props.fetchParams.meta_cluster_type,
    confType: props.fetchParams.conf_type,
    version: props.fetchParams.version,
    treeId: route.query.treeId as string,
    parentId: route.query.parentId as string,
  }));

  /**
   * 设置多份集群配置
   */
  watch(() => props.fetchParams.meta_cluster_type, (type) => {
    const extraParamertes = type && extraParamertesCluster[type as ClusterTypesValues];
    if (extraParamertes) {
      state.extraParametersCards = [...extraParamertes];
      for (let i = 0; i < state.extraParametersCards.length; i++) {
        getExtraConfig(i);
      }
    }
  }, { immediate: true });

  /**
   * 获取部分集群额外配置
   */
  function getExtraConfig(index: number) {
    const item = state.extraParametersCards[index];
    if (item) {
      item.loading = true;
      getLevelConfig(getFetchParams('proxy_version', item.conf_type) as GetLevelConfigParams)
        .then((res) => {
          item.data = res;
        })
        .finally(() => {
          item.loading = false;
        });
    }
  }

  // 更新基础信息
  function handleUpdateInfo({ key, value }: { key: string, value: string }) {
    Object.assign(props.data, { [key]: value });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .config-details {
    &__operations {
      .bk-button {
        width: 88px;
        margin-right: 8px;
      }
    }

    &__content {
      :deep(.bk-alert) {
        margin-bottom: 8px;
      }

      :deep(.db-card) {
        padding: 24px 0;
        margin-bottom: 0;
        box-shadow: none;

        &:last-child {
          padding-bottom: 0;
        }

        &.params-card {
          margin: 0;
        }
      }
    }
  }
</style>
