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
  <DbFormItem
    ref="formItemRef"
    :label="t('目标DB')"
    property="execute_objects"
    required
    :rules="rules">
    <RenderData>
      <RenderDataRow
        v-for="(item, index) in modelValue"
        :key="item.rowKey"
        ref="rowRef"
        :cluster-version-list="clusterVersionList"
        :data="item"
        :removeable="modelValue.length < 2"
        @add="(value: IDataRow) => handleAppend(value, index)"
        @change="(data: IDataRow) => handleChange(data, index)"
        @remove="handleRemove(index)" />
    </RenderData>
  </DbFormItem>
</template>
<script setup lang="tsx">
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RenderData from './RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './RenderData/Row.vue';

  interface Props {
    clusterVersionList: string[];
  }

  defineProps<Props>();

  const { t } = useI18n();

  const modelValue = defineModel<Array<IDataRow>>({
    default: () => [],
  });

  const formItemRef = ref();
  const rowRef = ref<InstanceType<typeof RenderDataRow>[]>();

  const rules = [
    {
      validator: () => Promise.all(rowRef.value!.map((item) => item.getValue())),
      message: t('目标DB设置不正确'),
      trigger: 'change',
    },
  ];

  watch(
    modelValue,
    () => {
      if (modelValue.value.length < 1) {
        modelValue.value = [createRowData()];
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (data: IDataRow, index: number) => {
    const result = [...modelValue.value];
    result.splice(index, 1, data);
    formItemRef.value.clearValidate();
    modelValue.value = result;
  };

  // 追加一个集群
  const handleAppend = (data: IDataRow, index: number) => {
    const result = [...modelValue.value];
    result.splice(index + 1, 0, data);
    formItemRef.value.clearValidate();
    modelValue.value = result;
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const result = [...modelValue.value];
    result.splice(index, 1);
    modelValue.value = result;
  };
</script>
