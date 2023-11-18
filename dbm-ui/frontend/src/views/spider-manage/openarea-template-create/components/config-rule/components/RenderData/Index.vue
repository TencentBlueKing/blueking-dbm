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
  <div class="render-data">
    <RenderTable>
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :width="200">
          {{ t('克隆 DB') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="170"
          :width="180">
          {{ t('克隆表结构') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="170"
          :width="180">
          {{ t('克隆表数据') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="190">
          {{ t('生成目标 DB 范式') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          required
          :width="180">
          {{ t('初始化授权') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          fixed="right"
          :required="false"
          :width="100">
          {{ t('操作') }}
        </RenderTableHeadColumn>
      </template>

      <template #data>
        <slot />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  const { t } = useI18n();
</script>
<style lang="less">
  .render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
