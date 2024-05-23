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
    :placeholder="t('请输入表名称，支持通配符“%”，含通配符的仅支持单个')"
    :rules="rules"
    :single="single"
    @change="handleChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableTagInput from '@components/render-table/columns/tag-input/index.vue';

  interface Props {
    modelValue?: string[];
    clusterId: number;
    required?: boolean;
    single?: boolean;
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
    required: true,
    single: false,
    rules: undefined,
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
        validator: (value: string[]) => !_.some(value, (item) => /\*/.test(item) && item.length > 1),
        message: t('* 只能独立使用'),
        trigger: 'change',
      },
      {
        validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
        message: t('% 不允许单独使用'),
        trigger: 'change',
      },
      {
        validator: (value: string[]) => {
          if (_.some(value, (item) => /[*%?]/.test(item))) {
            return value.length < 2;
          }
          return true;
        },
        message: t('含通配符的单元格仅支持输入单个对象'),
        trigger: 'change',
      },
    ];
  });

  // 集群改变时表名需要重置
  watch(
    () => props.clusterId,
    () => {
      localValue.value = [];
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
      return tagRef.value.getValue().then(() => {
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
