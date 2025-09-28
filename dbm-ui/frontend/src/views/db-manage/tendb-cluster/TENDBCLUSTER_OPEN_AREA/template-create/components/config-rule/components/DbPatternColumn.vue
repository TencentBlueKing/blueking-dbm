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
    :disabled-method="disabledMethod"
    field="target_db_pattern"
    :label="t('生成的目标DB名')"
    :min-width="200"
    required>
    <template #head>
      <BkPopover
        :content="t('可使用 { } 占位，如db_{id} ；{id}的实际值在执行开区时传入', { x: '{ }', y: '{id}' })"
        placement="top"
        theme="dark">
        <span style="border-bottom: 1px dashed #979ba5">{{ t('生成的目标DB名') }}</span>
      </BkPopover>
      <BatchEditColumn
        v-model="showBatchEdit"
        :placeholder="t('只能包含英文字母、数字，多个换行分隔')"
        :title="t('生成的目标DB名')"
        type="textarea"
        @change="(value: string) => handleBatchEdit(value)">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleShowBatchEdit">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue"
      :placeholder="t('可使用 { } 占位，如db_{id} ；{id}的实际值在执行开区时传入', { x: '{ }', y: '{id}' })">
    </EditableInput>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    clusterId: number;
    sourceDb: string;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();
  const route = useRoute();
  const isEditMode = route.name === 'TendbClusterOpenareaTemplateEdit';

  const disabledMethod = () => {
    if (!props.clusterId) {
      return t('请先选择集群');
    }
    return '';
  };

  const showBatchEdit = ref(false);

  const handleShowBatchEdit = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEdit = (value: string) => {
    emits('batch-edit', value, 'target_db_pattern');
  };

  watch(
    () => props.sourceDb,
    () => {
      if (!isEditMode && props.sourceDb && !modelValue.value) {
        modelValue.value = `${props.sourceDb}_{ID}`;
      }
    },
  );
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    margin-left: 4px;
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
