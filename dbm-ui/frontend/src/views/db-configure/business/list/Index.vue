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
    <ClusterTab v-model="activeTab" />
    <div class="content-main">
      <Content
        v-if="activeTab"
        :key="activeTab" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import ClusterTab from '@components/cluster-tab/Index.vue';

  import Content from './components/Content.vue';

  import { ClusterTypes } from '@/common/const';

  const router = useRouter();
  const route = useRoute();

  const activeTab = ref<ClusterTypes>((route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);

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
    height: calc(100vh - 105px);
    display: flex;
    flex-direction: column;

    .content-main {
      flex: 1;
      overflow: hidden;
    }
  }
</style>
