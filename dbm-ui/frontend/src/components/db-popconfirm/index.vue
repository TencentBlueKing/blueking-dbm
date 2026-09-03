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
    v-bind="$attrs"
    class="db-popconfirm"
    @click.stop="">
    <slot />
  </div>
  <div
    ref="popRef"
    :style="contentStyle">
    <div style="font-size: 16px; line-height: 20px; color: #313238">
      {{ title }}
    </div>
    <div style="margin-top: 10px; font-size: 12px; color: #63656e">
      <slot name="content">
        {{ content }}
      </slot>
    </div>
    <div style="margin-top: 16px; text-align: right">
      <BkButton
        class="mr-8"
        :loading="isConfirmLoading"
        size="small"
        :theme="theme"
        @click="handleConfirm">
        {{ confirmText || t('确认') }}
      </BkButton>
      <BkButton
        size="small"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type Placement, type SingleTarget } from 'tippy.js';
  import { onBeforeUnmount, onMounted, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    cancelHandler?: () => Promise<any> | void;
    confirmHandler: () => Promise<any> | void;
    /** 确认按钮文案，默认「确认」 */
    confirmText?: string;
    content?: string;
    /** 禁用后点击触发器不再弹出确认气泡 */
    disabled?: boolean;
    hideOnClick?: boolean;
    placement?: Placement;
    theme?: 'primary' | 'danger';
    title: string;
    width?: number;
  }

  type Emits = (e: 'toggleShow', value: boolean) => void;

  defineOptions({
    name: 'DbPopconfirm',
  });

  const props = withDefaults(defineProps<Props>(), {
    cancelHandler: () => Promise.resolve(),
    confirmText: '',
    content: '',
    disabled: false,
    hideOnClick: true,
    placement: 'top',
    theme: 'primary',
    width: 280,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  let tippyIns: Instance | undefined;
  let triggerObserver: MutationObserver | undefined;

  const rootRef = ref();
  const popRef = ref();
  const isConfirmLoading = ref(false);

  const contentStyle = computed(() => ({
    padding: '15px 10px',
    width: `${props.width}px`,
  }));

  const handleConfirm = () => {
    isConfirmLoading.value = true;
    Promise.resolve()
      .then(() => props.confirmHandler())
      .then(() => {
        tippyIns?.hide();
      })
      .finally(() => {
        isConfirmLoading.value = false;
      });
  };

  const handleCancel = () => {
    Promise.resolve()
      .then(() => props.cancelHandler())
      .then(() => {
        tippyIns?.hide();
      });
  };

  watch(
    () => props.disabled,
    () => {
      if (!tippyIns) {
        return;
      }
      if (props.disabled) {
        tippyIns.hide();
        tippyIns.disable();
        return;
      }
      tippyIns.enable();
    },
  );

  const destroyTippy = () => {
    if (!tippyIns) {
      return;
    }
    tippyIns.hide();
    tippyIns.unmount();
    tippyIns.destroy();
    tippyIns = undefined;
  };

  const createTippy = () => {
    const tippyTarget = rootRef.value?.children[0] as Element | undefined;

    if (!tippyTarget || tippyTarget === tippyIns?.reference) {
      return;
    }

    destroyTippy();
    tippyIns = tippy(tippyTarget as SingleTarget, {
      appendTo: () => document.body,
      arrow: true,
      content: popRef.value,
      hideOnClick: props.hideOnClick,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 12],
      onHide: () => {
        emits('toggleShow', false);
      },
      onShow: () => {
        emits('toggleShow', true);
      },
      placement: props.placement,
      popperOptions: {
        modifiers: [
          {
            name: 'flip',
            options: {
              allowedAutoPlacements: ['top-start', 'top-end'],
              fallbackPlacements: ['top', 'bottom'],
            },
          },
        ],
        strategy: 'fixed',
      },
      theme: 'light db-popconfirm-theme',
      trigger: 'click',
      zIndex: 999999,
    });

    if (props.disabled) {
      tippyIns.disable();
    }
  };

  onMounted(() => {
    createTippy();

    // 插槽里的触发元素可能被整体替换（如 AuthButton 鉴权结果返回后切换 v-if 分支），
    // 此时本组件不会重新渲染，只能靠观察子节点变化重新绑定，否则 tippy 还指向已卸载的元素
    triggerObserver = new MutationObserver(createTippy);
    triggerObserver.observe(rootRef.value, { childList: true });
  });

  onBeforeUnmount(() => {
    triggerObserver?.disconnect();
    triggerObserver = undefined;
    destroyTippy();
  });
</script>
<style lang="less">
  .db-popconfirm {
    display: inline-block;
  }

  .tippy-box[data-theme~='db-popconfirm-theme'] {
    background-color: #fff;
    border: 1px solid #dcdee5 !important;
    border-radius: 2px !important;
    box-shadow: 0 0 6px 0 #dcdee5 !important;

    .tippy-content {
      background-color: #fff;
    }

    // .tippy-arrow {
    //   position: absolute;
    //   bottom: -6px !important;
    //   left: 50% !important;
    //   background: #fff;
    //   border: 1px solid #dcdee5 !important;
    //   transform: translateX(-50%) rotateZ(45deg) !important;
    //   box-shadow: 0 0 6px 0 #dcdee5 !important;

    //   &::before {
    //     content: none;
    //   }
    // }

    // &[data-placement^='top-end'] {
    //   & > .tippy-arrow {
    //     right: -6px;
    //     left: unset !important;
    //   }
    // }
  }
</style>
