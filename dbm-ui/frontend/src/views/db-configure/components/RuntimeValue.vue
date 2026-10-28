<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <button
    class="param-runtime-value"
    :class="{
      'param-runtime-value-has-value': hasValues,
      'param-runtime-value-inconsistent': comparison === 'inconsistent',
    }"
    type="button"
    @click="emit('click')">
    <span
      v-bk-tooltips="{ content: tooltip, allowHTML: false, disabled: !tooltip }"
      class="param-runtime-value-text">
      {{ displayValue }}
    </span>
    <DbIcon
      v-if="comparison === 'unknown' && hasValues"
      class="param-runtime-value-warning"
      type="alert" />
  </button>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { RuntimeConfig } from '@views/db-configure/components/runtime-config';

  interface Props {
    encrypted?: boolean;
    runtime?: RuntimeConfig;
  }

  const props = withDefaults(defineProps<Props>(), {
    encrypted: false,
    runtime: undefined,
  });

  const emit = defineEmits<(e: 'click') => void>();

  const { t } = useI18n();
  const collator = new Intl.Collator(undefined, { numeric: true });
  const comparison = computed(() => props.runtime?.comparison ?? 'unknown');
  const values = computed(() =>
    [...(props.runtime?.values ?? [])].sort((left, right) => {
      const leftNumber = Number(left);
      const rightNumber = Number(right);
      if (left.trim() && right.trim() && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
        return leftNumber - rightNumber;
      }
      return collator.compare(left, right);
    }),
  );
  const hasValues = computed(() => values.value.some((value) => value.length > 0));
  const visibleValues = computed(() => values.value.map((value) => (props.encrypted ? '******' : value)));
  const displayValue = computed(() => {
    if (!hasValues.value) return '--';
    const text = visibleValues.value.slice(0, 3).join('，');
    return visibleValues.value.length > 3 ? `${text}…（${t('共n种', { n: visibleValues.value.length })}）` : text;
  });
  const tooltip = computed(() => {
    if (!hasValues.value) return props.runtime?.error ?? '';
    const lines = visibleValues.value.length > 1 ? [visibleValues.value.join('，')] : [];
    if (comparison.value === 'inconsistent') {
      lines.push(t('与设定值不一致'));
      if (props.runtime?.hasFailedInstances) lines.push(t('部分实例运行值获取失败'));
    } else if (comparison.value === 'unknown') {
      lines.push(t('实例运行值未完全获取，无法判断是否全部与设定值一致'));
    } else if (props.runtime?.equivalentExpressions) {
      lines.push(t('表达不同，语义一致'));
    }
    if (props.runtime?.error) lines.push(props.runtime.error);
    return lines.join('\n');
  });
</script>

<style lang="less" scoped>
  .param-runtime-value {
    display: inline-flex;
    max-width: 100%;
    padding: 0;
    overflow: hidden;
    font: inherit;
    color: #63656e;
    text-align: left;
    cursor: pointer;
    background: transparent;
    border: none;
    align-items: center;
    gap: 4px;

    .param-runtime-value-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .param-runtime-value-warning {
      color: #ff9c01;
      flex-shrink: 0;
    }
  }

  .param-runtime-value-has-value:hover {
    .param-runtime-value-text {
      text-decoration: underline;
    }

    &:not(.param-runtime-value-inconsistent) {
      color: #3a84ff;
    }
  }

  .param-runtime-value-inconsistent {
    color: #ff9c01;
  }
</style>
