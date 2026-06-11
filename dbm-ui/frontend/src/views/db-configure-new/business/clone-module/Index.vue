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
  <ApplyPermissionCatch>
    <Component
      :is="viewComponents[clusterType]"
      :key="clusterType"
      @router-back="routerBack" />
  </ApplyPermissionCatch>
</template>

<script setup lang="ts">
  import { useRoute } from 'vue-router';

  import { ClusterTypes } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';

  import MySql from './com-factory/MySql.vue';
  import SqlServer from './com-factory/SqlServer.vue';
  import TendbCluster from './com-factory/TendbCluster.vue';

  const route = useRoute();
  const router = useRouter();
  const clusterType = route.params.clusterType as ClusterTypes;

  const viewComponents = {
    [ClusterTypes.SQLSERVER_HA]: SqlServer,
    [ClusterTypes.SQLSERVER_SINGLE]: SqlServer,
    [ClusterTypes.TENDBCLUSTER]: TendbCluster,
    [ClusterTypes.TENDBHA]: MySql,
    [ClusterTypes.TENDBSINGLE]: MySql,
  } as Record<ClusterTypes, any>;

  const routerBack = () => {
    router.back();
  };

  defineExpose({
    routerBack,
  });
</script>
