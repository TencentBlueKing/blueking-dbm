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
  <div class="business-db-configure-list-page">
    <div
      v-show="isTabShow"
      style="height: 100%">
      <ClusterTabForBiz
        v-model="activeTab"
        v-model:is-show="isTabShow" />
      <div class="content-main">
        <Content
          v-if="activeTab"
          :key="activeTab" />
      </div>
    </div>
    <BkException
      v-show="!isTabShow"
      class="empty-exception"
      :description="t('暂无数据')"
      scene="part"
      type="empty" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import ClusterTabForBiz from '@components/cluster-tab-for-biz/Index.vue';

  import Content from './components/Content.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const activeTab = ref<ClusterTypes>(route.params.clusterType as ClusterTypes);
  const isTabShow = ref(false);
  /**
   * provide active tab
   */
  provide('activeTab', activeTab);

  watch(activeTab, (value, old) => {
    router.replace({
      params: {
        clusterType: value,
      },
      query: old ? {} : route.query, // 根据 old 判断是否为点击切换
    });
  });
</script>
<style lang="less">
  .business-db-configure-list-page {
    // display: flex;
    height: calc(100vh - var(--notice-height) - 105px);
    // flex-direction: column;

    .content-main {
      height: calc(100% - 42px);
      //   flex: 1;
      //   overflow: hidden;
    }

    .empty-exception {
      display: flex;
      height: 100%;
      background-color: #fff;
      align-items: center;
      justify-content: center;
    }
  }
</style>
