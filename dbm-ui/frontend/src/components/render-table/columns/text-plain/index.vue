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
  <BkLoading :loading="isLoading">
    <div
      ref="textRef"
      v-bk-tooltips="{
        content: data || placeholder,
        disabled: !isOverflow
      }"
      class="render-text-box"
      :class="{
        'default-display': !data,
        'is-error': Boolean(errorMessage),
      }">
      <span
        v-if="!data"
        style="color: #c4c6cc;">
        {{ placeholder }}
      </span>
      <span v-else>{{ data }}</span>
      <div
        v-if="errorMessage"
        class="input-error">
        <DbIcon
          v-bk-tooltips="errorMessage"
          type="exclamation-fill" />
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts" generic="T extends string | number">
  import { useIsWidthOverflow } from '@hooks';

  import useValidtor, { type Rules } from '../../hooks/useValidtor';

  interface Props {
    data?: T;
    isLoading?: boolean;
    placeholder?: string;
    rules?: Rules,
  }

  interface Exposes {
    getValue: () => Promise<T>
  }

  const props = defineProps<Props>();

  const textRef = ref();

  const renderData = computed(() => props.data);

  const { isOverflow } = useIsWidthOverflow(textRef, renderData);

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);

  defineExpose<Exposes>({
    getValue() {
      return validator(props.data).then(() => props.data as T);
    },
  });

</script>
<style lang="less" scoped>
  .is-error {
    background-color: #fff0f1 !important;
  }

  .render-text-box {
    position: relative;
    width: 100%;
    height: 42px;
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;

    .input-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      display: flex;
      padding-right: 10px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }

  }

  .default-display {
    cursor: not-allowed;
    background: #FAFBFD;
  }
</style>
