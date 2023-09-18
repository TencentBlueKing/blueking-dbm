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
  <MainBreadcrumbs v-if="showDetails && showCustomBreadcrumbs">
    <template #append>
      <div class="status">
        <span class="status__label">{{ $t('状态') }}：</span>
        <span class="status__value">
          <DbStatus :theme="statusInfo.theme">{{ statusInfo.text }}</DbStatus>
        </span>
      </div>
    </template>
  </MainBreadcrumbs>
  <StretchLayout
    class="wrapper"
    :has-details="showDetails"
    :style="{'--top-height': showDetails ? '52px' : '0px'}">
    <template #list="{ isCollapseRight, renderWidth, dragTrigger }">
      <List
        :drag-trigger="dragTrigger"
        :is-full-width="isCollapseRight || !showDetails"
        :width="renderWidth" />
    </template>
    <Details />
  </StretchLayout>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getClusterDetail } from '@services/es';

  import { useGlobalBizs, useMainViewStore  } from '@stores';

  import MainBreadcrumbs from '@components/layouts/MainBreadcrumbs.vue';
  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Details from './detail/Index.vue';
  import List from './list/index.vue';

  const { currentBizId } = useGlobalBizs();
  const route = useRoute();
  const { t } = useI18n();

  // 设置主视图padding
  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;

  const showCustomBreadcrumbs = ref(false);
  const clusterId = computed(() => Number(route.query.cluster_id));
  const showDetails = computed(() => !!clusterId.value);
  const statusInfo = shallowRef({
    theme: 'danger',
    text: t('异常'),
  });

  const fetchData = () => {
    getClusterDetail({
      bk_biz_id: currentBizId,
      cluster_id: clusterId.value,
    })
      .then((data) => {
        showCustomBreadcrumbs.value = true;
        mainViewStore.customBreadcrumbs = true;
        mainViewStore.$patch({
          breadCrumbsTitle: t('xx集群详情【inst】', { title: 'ES', inst: data.domain }),
        });

        if (data.status === 'normal') {
          statusInfo.value = {
            theme: 'success',
            text: t('正常'),
          };
        } else {
          statusInfo.value = {
            theme: 'danger',
            text: t('异常'),
          };
        }
      });
  };
  watch(clusterId, () => {
    if (clusterId.value) {
      fetchData();
    }
  }, {
    immediate: true,
  });
</script>

<style lang="less" scoped>
.wrapper {
  height: calc(100% - var(--top-height));
}
</style>
