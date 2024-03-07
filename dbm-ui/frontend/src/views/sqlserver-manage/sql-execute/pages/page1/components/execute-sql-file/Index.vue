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
  <BkFormItem
    :label="$t('SQL来源')"
    required>
    <BkRadioGroup
      v-model="importModel"
      @change="handleImportModeChange">
      <BkRadioButton
        label="manual"
        style="width: 140px">
        {{ $t('手动输入') }}
      </BkRadioButton>
      <BkRadioButton
        label="file"
        style="width: 140px">
        {{ $t('SQL文件') }}
      </BkRadioButton>
    </BkRadioGroup>
  </BkFormItem>
  <KeepAlive>
    <Component
      :is="renderCom"
      ref="fileRef"
      :model-value="modelValue"
      @change="handleChange"
      @grammar-check="handleGrammarCheck" />
  </KeepAlive>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';

  import LocalFile from './local-file/Index.vue';
  import ManualInput from './manual-input/Index.vue';

  interface Emits {
    (e: 'grammar-check', doCheck: boolean, checkPass: boolean): void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const fileRef = ref();
  const importModel = ref('manual');

  const comMap = {
    manual: ManualInput,
    file: LocalFile,
  };
  const renderCom = computed(() => comMap[importModel.value as keyof typeof comMap]);

  // 文件来源改变时需要重置文件列表和语法检测
  const handleImportModeChange = () => {
    modelValue.value = [];
  };

  // 文件列表
  const handleChange = (value: string[]) => {
    modelValue.value = value;
  };

  // 语法检测状态
  const handleGrammarCheck = (doCheck: boolean, checkPass: boolean) => {
    emits('grammar-check', doCheck, checkPass);
  };
</script>
<style lang="less" scoped>
  .label-tips {
    position: absolute;
    top: 0;
    padding-left: 16px;
    font-weight: normal;
    color: @gray-color;
  }
</style>
