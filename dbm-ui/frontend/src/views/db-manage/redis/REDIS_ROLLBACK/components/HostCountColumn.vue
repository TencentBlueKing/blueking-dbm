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
    :append-rules="rules"
    :disabled-method="disabledMethod"
    field="hostCount"
    :label="t('构造主机数量')"
    required
    :width="150">
    <template #head>
      <div v-bk-tooltips="tooltips">
        <span class="host-count-title">{{ t('构造主机数量') }}</span>
      </div>
    </template>
    <EditableInput
      v-model="modelValue"
      :max="max"
      :min="1"
      type="number"
      @change="handleUserInput" />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    // 参与构造的分片数；0 表示未选备份记录（不可编辑，值为 1），-1 表示上限未知（克隆单回填，不限制）
    max: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();

  // 与目标规格列相同的表头 tooltip 形态
  const tooltips = t('上限 = 参与构造的分片数，默认取上限。');

  const rules = [
    {
      message: t('构造主机数量不能为空'),
      trigger: 'change',
      validator: (value: number) => Boolean(value),
    },
    {
      message: t('不能超过参与构造的分片数'),
      trigger: 'change',
      validator: (value: number) => props.max <= 0 || Number(value) <= props.max,
    },
  ];

  // 用户是否手动修改过：未修改过随上限重算，修改过后仅在下限时下调
  let isTouched = false;

  const disabledMethod = () => (props.max === 0 ? t('请先选择备份记录') : false);

  const handleUserInput = () => {
    isTouched = true;
  };

  watch(
    () => props.max,
    (max) => {
      // 未选备份记录时固定为 1 不可编辑
      if (max === 0) {
        isTouched = false;
        modelValue.value = 1;
        return;
      }
      // 上限未知（克隆单回填）时保留原值不联动
      if (max < 0) {
        return;
      }
      if (!isTouched) {
        // 未手动修改过，默认取上限
        modelValue.value = max;
      } else if (modelValue.value > max) {
        // 手动修改过且超出新上限，下调并提示
        modelValue.value = max;
        Message({
          message: t('已按分片数下调'),
          theme: 'warning',
        });
      }
    },
    { immediate: true },
  );
</script>

<style lang="less" scoped>
  .host-count-title {
    border-bottom: 1px dashed #979ba5;
  }
</style>
