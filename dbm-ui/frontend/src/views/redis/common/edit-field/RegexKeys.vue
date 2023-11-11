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
  <TableTagInput
    ref="editTagRef"
    :model-value="localValue"
    :placeholder="t('请输入正则表达式')"
    :rules="rules"
    @change="handleChange">
    <template #tip>
      <p style="font-weight: bold;">
        {{ $t('可使用通配符进行提取，如：') }}
      </p>
      <p>{{ $t('*Key$ ：提取以 Key 结尾的 key，包括 Key') }}</p>
      <p>{{ $t('^Key$：提取精确匹配的Key') }}</p>
      <p>{{ $t('* ：代表所有') }}</p>
    </template>
  </TableTagInput>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableTagInput from '@components/tools-table-tag-input/index.vue';

  interface Props {
    data: string [],
    required?: boolean
  }
  interface Emits {
    (e: 'change', value: string[]): void
  }
  interface Exposes {
    getValue: () => Promise<string []>
  }

  const props = withDefaults(defineProps<Props>(), {
    required: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string []) => {
        if (!props.required) {
          return true;
        }
        return value && value.length > 0;
      },
      message: t('不能为空'),
    },
  ];

  const editTagRef = ref();
  const localValue = ref(props.data);

  const handleChange = (value: string[]) => {
    if (value.includes('*') && value.length > 1) {
      // 已经输入默认全部，不能继续输入其他字符
      localValue.value = ['*'];
    }
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return editTagRef.value.getValue(localValue.value);
    },
  });
</script>
