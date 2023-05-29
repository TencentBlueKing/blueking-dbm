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
    :label="t('脚本来源')"
    required>
    <BkRadioGroup v-model="importMode">
      <BkRadioButton
        label="manual"
        style="width: 140px;">
        {{ t('手动输入') }}
      </BkRadioButton>
      <BkRadioButton
        label="file"
        style="width: 140px;">
        {{ t('脚本文件') }}
      </BkRadioButton>
    </BkRadioGroup>
  </BkFormItem>
  <KeepAlive>
    <Component
      :is="renderCom"
      ref="fileRef"
      @change="handleContentChange" />
  </KeepAlive>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import LocalFile from './local-file/Index.vue';
  import ManualInput from './manual-input/Index.vue';
  interface Exposes {
    getValue: () => {
      scripts: {
        name: string,
        content: string,
      }[],
      mode: string,
    }
  }

  const modelValue = defineModel<string[]>();
  const importMode = defineModel<string>('importMode', {
    default: 'manual',
  });

  const { t } = useI18n();

  const fileRef = ref();

  const comMap = {
    manual: ManualInput,
    file: LocalFile,
  };

  const renderCom = computed(() => comMap[importMode.value as keyof typeof comMap]);

  const handleContentChange = (value: string[]) => {
    modelValue.value = value;
  };

  defineExpose<Exposes>({
    getValue: () => ({
      scripts: fileRef.value.getValue(),
      mode: importMode.value,
    }),
  });

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
