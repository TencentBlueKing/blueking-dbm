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
  <div
    ref="rootRef"
    class="render-table-name">
    <span @click="handleShowTips">
      <TableEditTag
        ref="tagRef"
        :model-value="modelValue"
        placeholder="请输入DB 名称，支持通配符“%”，含通配符的仅支持单个"
        :rules="rules"
        @change="handleChange" />
    </span>
    <div
      ref="popRef"
      style=" font-size: 12px; line-height: 24px; color: #63656e;">
      <p>%：匹配任意长度字符串，如 a%， 不允许独立使用</p>
      <p>？： 匹配任意单一字符，如 a%?%d</p>
      <p>* ：专门指代 ALL 语义, 只能独立使用</p>
      <p>注：含通配符的单元格仅支持输入单个对象</p>
      <p>Enter 完成内容输入</p>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    ref,
    watch,
  } from 'vue';

  import TableEditTag from '@views/mysql/common/edit/Tag.vue';

  interface Props {
    modelValue?: string [],
    clusterId: number,
    required?: boolean,
  }

  interface Emits {
    (e: 'change', value: string []): void
  }

  interface Exposes {
    getValue: (field: string) => Promise<Record<string, string[]>>
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    required: true,
  });

  const emits = defineEmits<Emits>();

  const rules = [
    {
      validator: (value: string []) => {
        if (!props.required) {
          return true;
        }
        return value && value.length > 0;
      },
      message: 'DB 名不能为空',
    },
    {
      validator: (value: string []) => {
        const hasAllMatch = _.find(value, item => /%$/.test(item));
        return !(value.length > 1 && hasAllMatch);
      },
      message: '一格仅支持单个 % 对象',
    },
  ];

  const rootRef = ref();
  const popRef = ref();
  const tagRef = ref();
  const localValue  = ref(props.modelValue);

  // 集群改变时表名需要重置
  watch(() => props.clusterId, () => {
    localValue.value = [];
  });

  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localValue.value = props.modelValue;
    } else {
      localValue.value = [];
    }
  }, {
    immediate: true,
  });

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('change', value);
  };

  let tippyIns: Instance | undefined;

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'top',
      appendTo: () => document.body,
      theme: 'light',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: true,
      offset: [0, 8],
      zIndex: 999999,
      hideOnClick: true,
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  defineExpose<Exposes>({
    getValue(field: string) {
      return tagRef.value.getValue()
        .then(() => ({
          [field]: localValue.value,
        }));
    },
  });
</script>
