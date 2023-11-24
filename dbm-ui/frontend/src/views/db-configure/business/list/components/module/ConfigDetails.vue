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
      <DetailsBase
        class="config-details-content"
        :data="data"
        :fetch-params="fetchParams"
        :level="ConfLevels.MODULE"
        :loading="false"
        :route-params="routeParams"
        :sticky-top="-16"
        @update-info="handleUpdateInfo" />
    </BkLoading>
  </div>
</template>

<script setup lang="ts">

  import {
    getConfigBaseDetails,
    getLevelConfig,
  } from '@services/source/configs';

  import { ConfLevels } from '@common/const';

  import DetailsBase from '@views/db-configure/components/DetailsBase.vue';

  type PlatConfDetailsParams = ServiceParameters<typeof getConfigBaseDetails>

  interface Props {
    data?: ServiceReturnType<typeof getLevelConfig>
    loading?: boolean,
    fetchParams?: PlatConfDetailsParams | ServiceParameters<typeof getLevelConfig>,
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({
      conf_items: [] as NonNullable<Props['data']>['conf_items'],
    } as NonNullable<Props['data']>),
    loading: false,
    fetchParams: () => ({} as PlatConfDetailsParams),
  });

  const route = useRoute();

  // 编辑路由参数
  const routeParams = computed(() => ({
    clusterType: props.fetchParams.meta_cluster_type,
    confType: props.fetchParams.conf_type,
    version: props.fetchParams.version,
    treeId: route.query.treeId as string,
    parentId: route.query.parentId as string,
  }));

  // 更新基础信息
  function handleUpdateInfo({ key, value }: { key: string, value: string }) {
    Object.assign(props.data, { [key]: value });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .config-details {
    height: 100%;

    .config-details-content {
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
