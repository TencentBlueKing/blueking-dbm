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
    class="member-selector-wrapper"
    :class="{ 'is-hover': isHover }"
    @mouseenter="handleHover"
    @mouseleave="handleBlur">
    <TenantSelector
      v-if="tenantId"
      v-model="modelValue" />
    <CommonSelector
      v-else
      v-model="modelValue" />
    <DbIcon
      v-if="modelValue.length > 0"
      v-bk-tooltips="t('复制')"
      class="db-member-selector-copy"
      type="copy"
      @click.stop="handleCopy" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import { execCopy } from '@utils';

  import CommonSelector from './components/CommonSelector.vue';
  import TenantSelector from './components/TenantSelector.vue';

  const emits = defineEmits<(e: 'change', value: string[]) => void>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { tenantId } = useUserProfile();
  const { t } = useI18n();

  const isHover = ref(false);

  watch(modelValue, () => {
    emits('change', modelValue.value);
  });

  const handleHover = () => {
    isHover.value = true;
  };

  const handleBlur = () => {
    isHover.value = false;
  };

  const handleCopy = () => {
    execCopy(modelValue.value.join(';'), t('复制成功，共n条', { n: modelValue.value.length }));
  };
</script>

<style lang="less" scoped>
  .member-selector-wrapper {
    position: relative;
    line-height: 1;

    &.is-hover {
      :deep(.user-selector-clear) {
        visibility: visible;
      }
    }

    &:hover {
      .db-member-selector-copy {
        display: block;
      }
    }

    .db-member-selector-copy {
      position: absolute;
      top: 50%;
      right: 10px;
      z-index: 99;
      display: none;
      width: 20px;
      height: 20px;
      margin-top: -10px;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      cursor: pointer;
      background-color: white;

      &:hover {
        color: @primary-color;
        background-color: #e1ecff;
      }
    }
  }
</style>
