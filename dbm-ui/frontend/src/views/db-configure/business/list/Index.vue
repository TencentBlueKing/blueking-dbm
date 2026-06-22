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
    <ClusterTab
      v-model="activeClusterType"
      :excludes="[
        ClusterTypes.ORACLE_SINGLE_NONE,
        ClusterTypes.ORACLE_PRIMARY_STANDBY,
        ClusterTypes.K8S_SURREALDB_HA,
        ClusterTypes.K8S_SURREALDB_SINGLE,
        ClusterTypes.K8S_QDRANT_HA,
      ]" />
    <ApplyPermissionCatch :key="activeClusterType">
      <Content
        v-if="hasModule"
        class="content-main" />
      <ConfigBusiness
        v-else
        class="content-details"
        :cluster-type="activeClusterType" />
    </ApplyPermissionCatch>
  </div>
</template>
<script setup lang="ts">
  import { ClusterTypes } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import ClusterTab from '@components/cluster-tab/Index.vue';

  import { resetConfigureTab } from '@/views/db-configure/utils/configureState.ts';

  import ConfigBusiness from './components/biz/Index.vue';
  import Content from './components/Content.vue';

  const router = useRouter();
  const route = useRoute();

  const activeClusterType = ref<ClusterTypes>((route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);

  /**
   * provide active tab
   */
  provide('activeClusterType', activeClusterType);

  const hasModule = computed(() =>
    [
      ClusterTypes.SQLSERVER_HA,
      ClusterTypes.SQLSERVER_SINGLE,
      ClusterTypes.TENDBCLUSTER,
      ClusterTypes.TENDBHA,
      ClusterTypes.TENDBSINGLE,
    ].includes(activeClusterType.value),
  );

  watch(
    activeClusterType,
    (value, old) => {
      router.replace({
        params: {
          clusterType: value,
        },
      });

      // 切换 clusterTab 时重置 sessionStorage 中的 activeTab（不同集群类型的 tabs 不同）
      if (old) {
        resetConfigureTab();
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .business-db-configure-list-page {
    display: flex;
    height: calc(100vh - var(--notice-height) - 105px);
    flex-direction: column;

    .content-main {
      flex: 1;
    }

    .content-details {
      margin: 20px 24px;
    }
  }
</style>
