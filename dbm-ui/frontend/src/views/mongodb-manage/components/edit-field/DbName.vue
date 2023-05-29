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
    ref="tagRef"
    :model-value="localValue"
    :placeholder="t('请输入DB 名称，支持通配符“%”，含通配符的仅支持单个')"
    :rules="rules"
    :single="single"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableTagInput from '@components/render-table/columns/tag-input/index.vue';

  interface Props {
    required?: boolean,
    single?: boolean,
    rules?: {
      validator: (value: string[]) => boolean,
      message: string
    }[]
  }

  interface Emits {
    (e: 'change', value: string []): void,
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string[]>>
  }

  const props = withDefaults(defineProps<Props>(), {
    required: true,
    single: false,
    remoteExist: false,
    checkExist: false,
    rules: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tagRef = ref();
  const localValue = ref<string[]>([]);

  const rules = computed(() => {
    if (props.rules && props.rules.length > 0) {
      return props.rules;
    }

    return [
      {
        validator: (value: string []) => {
          if (!props.required) {
            return true;
          }
          return value && value.length > 0;
        },
        message: t('DB 名不能为空'),
      },
      {
        validator: (value: string []) => _.every(value, item => item.length <= 64),
        message: t('库名长度不超过64个字符'),
        trigger: 'change',
      },
      {
        validator: (value: string []) => _.every(value, item => /^[a-zA-Z0-9_-]*\*?[a-zA-Z0-9_-]*$/.test(item)),
        message: t('输入格式有误'),
        trigger: 'change',
      },
    ];
  });

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue(field: string) {
      return tagRef.value.getValue()
        .then(() => {
          if (!localValue.value) {
            return Promise.reject();
          }
          return {
            [field]: props.single ? localValue.value[0] : localValue.value,
          };
        });
    },
  });
</script>
