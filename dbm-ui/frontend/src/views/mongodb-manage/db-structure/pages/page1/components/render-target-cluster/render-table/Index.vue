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
  <div class="db-struct-render-data">
    <RenderTable :key="clusterType">
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :required="false"
          :width="190">
          {{ t('集群') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="350"
          :required="false"
          :width="400">
          {{ t('构造类型') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="90"
          :required="false"
          :width="210">
          {{ isBackupRecordType ? t('备份文件') : t('指定时间') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="96"
          :required="false"
          :width="120">
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

  interface Props {
    clusterType: string;
    isBackupRecordType: boolean;
  }

  defineProps<Props>();

  const { t } = useI18n();

</script>
<style lang="less">
  .db-struct-render-data {
    display: block;
    margin-top: 16px;

    .batch-edit-btn {
      display: inline-block;
      margin-left: 4px;
      line-height: 40px;
      color: #3a84ff;
      vertical-align: top;
      cursor: pointer;
    }
  }
</style>
