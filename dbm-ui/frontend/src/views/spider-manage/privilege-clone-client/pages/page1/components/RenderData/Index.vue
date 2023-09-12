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
      <template
        #default="slotProps">
        <RenderTableHeadColumn
          :min-width="320"
          :row-width="slotProps.rowWidth"
          :width="330">
          {{ t('源客户端IP') }}
          <template #append>
            <span
              class="batch-edit-btn"
              @click="handleShowIpSelector">
              <DbIcon type="batch-host-select" />
            </span>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="220"
          :row-width="slotProps.rowWidth"
          :width="240">
          {{ t('模块') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="220"
          :row-width="slotProps.rowWidth"
          :width="240">
          {{ t('所属云区域') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="320"
          :row-width="slotProps.rowWidth"
          :width="340">
          {{ t('新客户端IP') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :is-fixed="slotProps.isOverflow"
          :min-width="100"
          :required="false"
          :row-width="slotProps.rowWidth"
          :width="170">
          {{ t('操作') }}
        </RenderTableHeadColumn>
      </template>

      <template #data="slotProps">
        <slot :is-overflow="slotProps.isOverflow" />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderTableHeadColumn from '@views/spider-manage/common/render-table/HeadColumn.vue';
  import RenderTable from '@views/spider-manage/common/render-table/Index.vue';

  interface Emits{
    (e: 'showIpSelector'): void,
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleShowIpSelector = () => {
    emits('showIpSelector');
  };
</script>
<style lang="less">
  .render-data {
    display: block;

    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
