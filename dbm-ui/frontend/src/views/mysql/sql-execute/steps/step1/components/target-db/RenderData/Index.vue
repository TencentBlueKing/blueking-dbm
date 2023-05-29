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
  <RenderTable>
    <RenderTableHeadColumn>
      {{ $t('变更的DB') }}
      <span style="font-size: 12px; font-weight: normal; color: #8a8f99;">
        ({{ $t('如果变更 SQL 是“create database ...”，这个请填写 test') }})
      </span>
    </RenderTableHeadColumn>
    <RenderTableHeadColumn :required="false">
      {{ $t('忽略的DB') }}
    </RenderTableHeadColumn>
    <RenderTableHeadColumn
      :required="false"
      :width="90">
      {{ $t('操作') }}
    </RenderTableHeadColumn>
    <template #data>
      <slot />
    </template>
  </RenderTable>
</template>
<script setup lang="ts">
  import RenderTableHeadColumn from '@views/mysql/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/mysql/common/render-table/Index.vue';
</script>

