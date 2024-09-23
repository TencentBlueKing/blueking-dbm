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
          :required="false"
          :width="100">
          {{ t('克隆表结构') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="170"
          :required="false"
          :width="180">
          {{ t('克隆表数据') }}
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="190">
          <BkPopover
            :content="t('支持使用 { } 占位，如db_{id} , id在执行开区时传入', { x: '{ }', y: '{id}' })"
            placement="top"
            theme="dark">
            <span style="border-bottom: 1px dashed #979ba5">{{ t('生成的目标DB名') }}</span>
          </BkPopover>
          <template #append>
            <BatchEditColumn
              v-model="showBatchEdit"
              :placeholder="t('只能包含英文字母、数字，多个换行分隔')"
              :title="t('生成的目标DB名')"
              type="textarea"
              @change="(value: string) => handleBatchEdit(value)">
              <span
                v-bk-tooltips="t('批量编辑：通过换行分隔，快速批量录入多个值')"
                class="batch-edit-btn"
                @click="handleShowBatchEdit">
                <DbIcon type="piliangluru" />
              </span>
            </BatchEditColumn>
          </template>
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

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Emits {
    (e: 'batchEdit', value: string[]): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const showBatchEdit = ref(false);

  const handleShowBatchEdit = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEdit = (value: string) => {
    const list = value.trim().split('\n');
    emits('batchEdit', list);
  };
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
