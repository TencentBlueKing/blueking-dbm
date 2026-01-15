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
  <EditableColumn
    field="truncate_data_type"
    :label="t('清档类型')"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="list"
        :title="t('清档类型')"
        @change="handleBatchEdit">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleShowBatchEdit">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :list="list" />
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);

  const list = [
    {
      label: t('清除表数据_truncatetable'),
      value: 'truncate_table',
    },
    {
      label: t('清除表数据和结构_droptable'),
      value: 'drop_table',
    },
    {
      label: t('删除整库_dropdatabase'),
      value: 'drop_database',
    },
  ];

  const truncateTypeMap = {
    drop_database: 'drop_database',
    drop_table: 'drop_table',
    truncate_table: 'truncate_table',
  } as Record<string, string>;

  watch(
    modelValue,
    () => {
      modelValue.value = truncateTypeMap[modelValue.value];
    },
    {
      immediate: true,
    },
  );

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEdit = (value: string) => {
    emits('batch-edit', value, 'truncate_data_type');
  };
</script>

<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
