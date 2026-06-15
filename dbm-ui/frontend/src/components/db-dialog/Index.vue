<template>
  <BkDialog
    v-bind="{
      ...props,
      ...attrs,
    }"
    v-model:is-show="isShow"
    :before-close="beforeCloseCallback"
    class="db-dialog"
    :close-icon="closeIcon"
    :draggable="false"
    :quick-close="quickClose"
    :render-directive="renderDirective"
    :title="title"
    :width="width">
    <template
      v-if="slots.header"
      #header>
      <slot name="header" />
    </template>
    <slot />
    <template #footer>
      <slot name="footer">
        <BkButton
          v-if="showConfirm"
          class="mr-8"
          theme="primary"
          @click="handleConfirm">
          {{ confirmText || t('确定') }}
        </BkButton>
        <BkButton @click="handleCancle">
          {{ cancelText || t('取消') }}
        </BkButton>
      </slot>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useModelProvider } from '@hooks';

  import { leaveConfirm } from '@utils';

  interface Props {
    cancelText?: string;
    closeIcon?: boolean;
    confirmText?: string;
    quickClose?: boolean;
    renderDirective?: 'if' | 'show';
    showConfirm?: boolean;
    title?: string;
    width?: number | string;
  }
  type Emits = (e: 'update:isShow', isShow: boolean) => void;

  const props = withDefaults(defineProps<Props>(), {
    cancelText: '',
    closeIcon: true,
    confirmText: '',
    isShow: false,
    quickClose: true,
    renderDirective: 'if',
    showConfirm: true,
    title: '',
    width: undefined,
  });

  const emit = defineEmits<Emits>();

  const slots = defineSlots<{
    default?: () => VNode;
    footer?: () => VNode;
    header?: () => VNode;
  }>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const attrs = useAttrs();
  const { t } = useI18n();
  const getModelProvier = useModelProvider();

  let pageChangeConfirm: boolean | 'popover' = false;

  watch(
    isShow,
    (newValue) => {
      if (newValue) {
        pageChangeConfirm = window.changeConfirm;
        window.changeConfirm = 'popover';
      }
    },
    {
      immediate: true,
    },
  );

  const beforeCloseCallback = () => {
    return leaveConfirm();
  };

  const close = () => {
    window.changeConfirm = pageChangeConfirm;
    emit('update:isShow', false);
  };

  // 确定
  const handleConfirm = () => {
    const { submit } = getModelProvier();
    submit().then(() => {
      close();
    });
  };

  // 取消
  const handleCancle = () => {
    const { cancel } = getModelProvier();

    return leaveConfirm()
      .then(() => cancel())
      .then(() => close());
  };
</script>
