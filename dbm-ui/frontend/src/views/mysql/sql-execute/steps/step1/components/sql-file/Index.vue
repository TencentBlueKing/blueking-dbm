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
      v-model="localImportMode"
      @change="handleImportModeChange">
      <BkRadioButton
        label="manual"
        style="width: 140px;">
        {{ $t('手动输入') }}
      </BkRadioButton>
      <BkRadioButton
        label="file"
        style="width: 140px;">
        {{ $t('SQL文件') }}
      </BkRadioButton>
    </BkRadioGroup>
  </BkFormItem>
  <KeepAlive>
    <Component
      :is="renderCom"
      ref="fileRef"
      :model-value="localFileList"
      @change="handleChange"
      @grammar-check="handleGrammarCheck" />
  </KeepAlive>
</template>
<script setup lang="ts">
  import {
    computed,
    ref,
    watch,
  } from 'vue';

  import LocalFile from './local-file/Index.vue';
  import ManualInput from './manual-input/Index.vue';

  interface Props {
    importMode: string;
    modelValue: string[];
  }
  interface Emits {
    (e: 'update:modelValue', value: string []): void;
    (e: 'update:importMode', value: string): void;
    (e: 'grammar-check', doCheck: boolean, checkPass: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const fileRef = ref();
  const localImportMode = ref(props.importMode);
  const localFileList = ref<string[]>([]);

  const comMap = {
    manual: ManualInput,
    file: LocalFile,
  };
  const renderCom = computed(() => comMap[localImportMode.value as keyof typeof comMap]);

  watch(() => props.importMode, () => {
    localImportMode.value = props.importMode;
  });

  watch(() => props.modelValue, () => {
    localFileList.value = props.modelValue;
  });

  // 文件来源改变时需要重置文件列表和语法检测
  const handleImportModeChange = () => {
    localFileList.value = [];
  };

  // 文件列表
  const handleChange = (value: string []) => {
    emits('update:modelValue', value);
    emits('update:importMode', localImportMode.value);
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
