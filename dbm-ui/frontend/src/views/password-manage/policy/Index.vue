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
  <DbTab
    v-model:active="activeTab"
    :exclude="[DBTypes.RIAK]" />
  <div class="password-policy-content">
    <RenderContent :db-type="activeTab" />
  </div>
</template>

<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import RenderContent from './components/Content.vue';

  const route = useRoute();

  const activeTab = ref<DBTypes>(route.query.db_type as DBTypes);
</script>

<style lang="less">
  .password-policy-content {
    padding: 16px 20px;
  }
</style>
