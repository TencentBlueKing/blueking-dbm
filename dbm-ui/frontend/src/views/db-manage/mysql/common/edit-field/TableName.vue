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
    :disabled="disabled"
    :model-value="localValue"
    :placeholder="placeholder ? placeholder : t('请输入表名称，支持通配符“%”，含通配符的仅支持单个')"
    :rules="rules"
    :single="single"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableTagInput from '@components/render-table/columns/db-table-name/Index.vue';

  interface Props {
    modelValue?: string[];
    initValue?: string[];
    disabled?: boolean;
    clusterId?: number;
    required?: boolean;
    placeholder?: string;
    single?: boolean;
    allowAsterisk?: boolean; // 是否允许单个 *
    rules?: {
      validator: (value: string[]) => boolean;
      message: string;
    }[];
  }

  interface Emits {
    (e: 'change', value: string[]): void;
    (e: 'update:modelValue', value: string[]): void;
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string[]>>;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    initValue: undefined,
    placeholder: '',
    clusterId: undefined,
    required: true,
    single: false,
    rules: undefined,
    disabled: false,
    allowAsterisk: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tagRef = ref();
  const localValue = ref(props.modelValue);

  const rules = computed(() => {
    if (props.rules && props.rules.length > 0) {
      return props.rules;
    }

    return [
      {
        validator: (value: string[]) => {
          if (!props.required) {
            return true;
          }
          return value && value.length > 0;
        },
        message: t('表名不能为空'),
      },
      {
        validator: (value: string[]) => _.every(value, (item) => /^[-_a-zA-Z0-9*?%]{0,35}$/.test(item)),
        message: t('库表名支持数字、字母、中划线、下划线，最大35字符'),
      },
      {
        validator: (value: string[]) => {
          if (props.allowAsterisk) {
            return true;
          }

          return _.every(value, (item) => item !== '*');
        },
        message: t('不允许为 *'),
      },
      {
        validator: (value: string[]) =>
          !_.some(value, (item) => (/\*/.test(item) && item.length > 1) || (value.length > 1 && item === '*')),
        message: t('* 只能独立使用'),
      },
      {
        validator: (value: string[]) => _.every(value, (item) => !/^[%?]$/.test(item)),
        message: t('% 或 ? 不允许单独使用'),
      },
      {
        validator: (value: string[]) => {
          if (_.some(value, (item) => /[*%?]/.test(item))) {
            return value.length < 2;
          }
          return true;
        },
        message: t('含通配符的单元格仅支持输入单个对象'),
      },
      // TODO: 表不存在
    ];
  });

  // 集群改变时表名需要重置
  watch(
    () => props.clusterId,
    () => {
      if (props.initValue) {
        localValue.value = props.initValue;
      } else {
        localValue.value = [];
      }
    },
  );

  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localValue.value = props.modelValue;
      } else {
        localValue.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('update:modelValue', value);
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue(field: string) {
      return tagRef.value
        .getValue()
        .then(() => {
          if (!localValue.value) {
            return Promise.reject();
          }
          return {
            [field]: props.single ? localValue.value[0] : localValue.value,
          };
        })
        .catch(() =>
          Promise.reject({
            [field]: props.single ? localValue.value?.[0] || '' : localValue.value,
          }),
        );
    },
  });
</script>
