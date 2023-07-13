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
    class="render-db-name">
    <span @click="handleShowTips">
      <TableEditTag
        ref="editTagRef"
        :model-value="localValue"
        :placeholder="$t('请输入正则表达式')"
        :rules="rules"
        @change="handleChange" />
    </span>
    <div
      ref="popRef"
      style=" font-size: 12px; line-height: 24px;color: #63656e;">
      <p style="font-weight: bold;">
        {{ $t('可使用通配符进行提取，如：') }}
      </p>
      <p>{{ $t('*Key$ ：提取以 Key 结尾的 key，包括 Key') }}</p>
      <p>{{ $t('^Key$：提取精确匹配的Key') }}</p>
      <p>{{ $t('* ：代表所有') }}</p>
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
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TableEditTag from '@views/redis/common/edit/Tag.vue';

  interface Props {
    data: string []
  }
  interface Emits {
    (e: 'change', value: string[]): void
  }
  interface Exposes {
    getValue: () => Promise<string []>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const rootRef = ref();
  const popRef = ref();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string []) =>  value.length > 0,
      message: t('包含 Key 不能为空'),
    },
  ];

  const editTagRef = ref();
  const localValue = ref(props.data);

  const handleChange = (value: string[]) => {
    console.log('input: ', value);
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
    getValue() {
      return editTagRef.value.getValue(localValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .render-db-name {
    display: block;
  }
</style>
