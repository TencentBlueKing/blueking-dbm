<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->
<template>
  <ClusterDetail :cluster-id="clusterId" />
</template>
<script setup lang="ts">
  import { useRoute, useRouter } from 'vue-router';

  import ClusterDetail from '../common/standard-cluster-detail/Index.vue';

  const route = useRoute();
  const router = useRouter();

  const clusterId = Number(route.params.clusterId);

  defineExpose({
    routerBack() {
      router.push({
        name: 'VictoriametricsStandardList',
      });
    },
  });
</script>
