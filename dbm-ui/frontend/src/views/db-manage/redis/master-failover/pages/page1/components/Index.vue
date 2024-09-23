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
          :width="280">
          <span>{{ t('主库主机') }}</span>
          <template #append>
            <BkPopover
              :content="t('批量添加')"
              theme="dark">
              <span
                class="batch-edit-btn"
                @click="handleShowMasterBatchSelector">
                <DbIcon type="batch-host-select" />
              </span>
            </BkPopover>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="280">
          <span>{{ t('所属集群') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="140"
          :required="false"
          :width="280">
          <span>{{ t('待切换的Master实例') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="130"
          :required="false"
          :width="280">
          <span>{{ t('待切换的从库主机') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="200">
          <span>{{ t('切换模式') }}</span>
          <template #append>
            <BatchEditColumn
              v-model="isShowBatchEdit"
              :data-list="selectList"
              :title="t('切换模式')"
              @change="handleBatchEdit">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleShowBatchEdit">
                <DbIcon type="bulk-edit" />
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

  import { OnlineSwitchType } from './RenderSwitchMode.vue';

  interface Emits {
    (e: 'showMasterBatchSelector'): void;
    (e: 'batchEditBackupLocal', value: string): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);

  const selectList = [
    {
      value: OnlineSwitchType.USER_CONFIRM,
      label: t('需人工确认'),
    },
    {
      value: OnlineSwitchType.NO_CONFIRM,
      label: t('无需确认'),
    },
  ];

  const handleShowMasterBatchSelector = () => {
    emits('showMasterBatchSelector');
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = !isShowBatchEdit.value;
  };

  const handleBatchEdit = (value: string | string[]) => {
    emits('batchEditBackupLocal', value as string);
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

  .spec-title {
    border-bottom: 1px dashed #979ba5;
  }
</style>
