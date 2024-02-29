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
  <BkFormItem :label="$t('执行前备份')">
    <BkSwitcher
      v-model="isNeedBackup"
      size="small"
      theme="primary"
      @change="handleNeedBackupChange" />
  </BkFormItem>
  <BkFormItem
    v-if="isNeedBackup"
    :label="$t('备份设置')"
    property="backup"
    required
    :rules="rules">
    <RenderData>
      <RenderDataRow
        v-for="(item, index) in localValue"
        :key="item.rowKey"
        ref="rowRef"
        :data="item"
        :removeable="localValue.length < 2"
        @add="(value: IDataRow) => handleAppend(value, index)"
        @change="(data: IDataRow) => handleChange(data, index)"
        @remove="handleRemove(index)" />
    </RenderData>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { ref, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderData from './RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './RenderData/Row.vue';

  interface Props {
    modelValue: Array<IDataRow>;
  }
  interface Emits {
    (e: 'update:modelValue', value: Array<IDataRow>): void;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<Emits>();

  const { t } = useI18n();
  const isNeedBackup = ref(false);

  const rowRef = ref();
  const localValue = shallowRef<IDataRow[]>([]);

  const rules = [
    {
      validator: () => Promise.all(rowRef.value.map((item: { getValue: () => Promise<string[]> }) => item.getValue())),
      message: t('备份设置不能为空'),
      trigger: 'change',
    },
  ];

  watch(
    () => props.modelValue,
    () => {
      isNeedBackup.value = props.modelValue.length > 0;
      localValue.value = props.modelValue;
    },
  );

  // 切换开启备份
  const handleNeedBackupChange = (checked: boolean) => {
    if (checked) {
      emit('update:modelValue', [createRowData()]);
    } else {
      emit('update:modelValue', []);
    }
  };

  const handleChange = (data: IDataRow, index: number) => {
    const result = [...props.modelValue];
    result.splice(index, 1, data);
    emit('update:modelValue', result);
  };

  // 追加一个 DB
  const handleAppend = (data: IDataRow, index: number) => {
    const result = [...props.modelValue];
    result.splice(index + 1, 0, data);
    emit('update:modelValue', result);
  };

  // 删除一个 DB
  const handleRemove = (index: number) => {
    const result = [...props.modelValue];
    result.splice(index, 1);
    emit('update:modelValue', result);
  };
</script>
