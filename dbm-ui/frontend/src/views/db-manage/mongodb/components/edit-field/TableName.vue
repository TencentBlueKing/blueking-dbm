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
    :placeholder="t('请输入表名称，支持通配符“*”')"
    :rules="rules"
    :single="single"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus">
    <template #tip>
      <div class="db-table-tag-tip">
        <div style="font-weight: 700">{{ t('库表输入说明') }}：</div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('不允许输入系统库和特殊库，如admin、config、local') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名要么同时为空, 要么同时不为空') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('支持通配符 *（指代任意长度字符串）') }}</span>
        </div>
        <div>
          <div class="circle-dot"></div>
          <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
        </div>
      </div>
    </template>
  </TableTagInput>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TableTagInput from '@components/render-table/columns/tag-input/index.vue';

  interface Props {
    data?: string[];
    compareData?: string[];
    required?: boolean;
    single?: boolean;
    rules?: {
      validator: (value: string[]) => boolean;
      message: string;
    }[];
  }

  interface Emits {
    (e: 'change', value: string[]): void;
  }

  interface Exposes {
    getValue: (field: string, isSubmit?: boolean) => Promise<Record<string, string[]>>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    compareData: undefined,
    required: true,
    single: false,
    rules: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let isSubmitting = false;

  const tagRef = ref();
  const localValue = ref<string[]>([]);

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
        validator: (value: string[]) => _.every(value, (item) => item.length <= 255),
        message: t('表名长度不超过255个字符'),
        trigger: 'change',
      },
      {
        validator: (value: string[]) => _.every(value, (item) => /^[a-zA-Z0-9_-]*\*?[a-zA-Z0-9_-]*$/.test(item)),
        message: t('输入格式有误'),
        trigger: 'change',
      },
      {
        validator: (value: string[]) => {
          if (!isSubmitting) {
            return true;
          }
          const { compareData } = props;
          if (compareData) {
            return (value.length === 0 && compareData.length === 0) || (value.length > 0 && compareData.length > 0);
          }
          return true;
        },
        message: t('忽略DB名、忽略表名要么同时为空, 要么同时不为空'),
        trigger: 'change',
      },
    ];
  });

  watchEffect(() => {
    localValue.value = props.data || [];
  });

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('change', value);
  };

  const handleFocus = () => {
    isSubmitting = false;
  };

  const handleBlur = () => {
    const { compareData } = props;
    if (compareData) {
      tagRef.value.getValue();
    }
  };

  defineExpose<Exposes>({
    getValue(field: string, submit = false) {
      isSubmitting = submit;
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

<style lang="less" scoped>
  .db-table-tag-tip {
    display: flex;
    padding: 3px 7px;
    line-height: 24px;
    flex-direction: column;

    div {
      display: flex;
      align-items: center;

      .circle-dot {
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-right: 6px;
        background-color: #63656e;
        border-radius: 50%;
      }
    }
  }
</style>
