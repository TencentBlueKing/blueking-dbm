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
  <BkSideslider
    v-bind="attrs"
    :before-close="beforeCloseCallback"
    :is-show="isShow"
    @update:is-show="handleUpdateShow">
    <template
      v-if="slots.header"
      #header>
      <slot name="header" />
    </template>
    <template #default>
      <div v-if="isShow">
        <slot />
      </div>
    </template>
    <template #footer>
      <template v-if="showFooter">
        <slot name="footer">
          <BkButton
            class="mr8"
            :disabled="disabledConfirm"
            :loading="isLoading"
            style="width: 102px;"
            theme="primary"
            @click="handleConfirm">
            {{ confirmText || $t('提交') }}
          </BkButton>
          <BkButton
            style="min-width: 64px;"
            @click="handleCancle">
            {{ cancelText || $t('取消') }}
          </BkButton>
        </slot>
      </template>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import {
    ref,
    useAttrs,
    useSlots,
    watch  } from 'vue';

  import { useModelProvider } from '@hooks';

  import { leaveConfirm } from '@utils';

  interface Props {
    isShow: boolean,
    showFooter?: boolean,
    confirmText?: string,
    cancelText?: string,
    disabledConfirm?: boolean,
  }

  interface Emits{
    (e: 'update:isShow', isShow: boolean):void
  }
  interface Exposes {
    handleConfirm: () => void,
    handleCancle: () => void,
  }

  const props = withDefaults(defineProps<Props>(), {
    isShow: false,
    showFooter: true,
    disabledConfirm: false,
    confirmText: '',
    cancelText: '',
  });

  const emit = defineEmits<Emits>();

  const attrs = useAttrs();
  const slots = useSlots();

  const isLoading = ref(false);
  let pageChangeConfirm: boolean | 'popover' = false;

  watch(() => props.isShow, (isShow) => {
    if (isShow) {
      pageChangeConfirm = window.changeConfirm;
      window.changeConfirm = 'popover';
    }
  }, {
    immediate: true,
  });

  const getModelProvier = useModelProvider();

  const beforeCloseCallback = () => {
    console.log('beforeCloseCallback = ', window.changeConfirm);
    return leaveConfirm();
  };
  const close = () => {
    window.changeConfirm = pageChangeConfirm;
    emit('update:isShow', false);
  };

  const handleUpdateShow = () => {
    close();
  };

  // 确定
  const handleConfirm = () => {
    isLoading.value = true;
    const { submit } = getModelProvier();
    submit()
      .then(() => {
        close();
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  // 取消
  const handleCancle = () => {
    const { cancel } = getModelProvier();
    leaveConfirm()
      .then(() => cancel())
      .then(() => close());
  };

  defineExpose<Exposes>({
    handleConfirm,
    handleCancle,
  });
</script>
