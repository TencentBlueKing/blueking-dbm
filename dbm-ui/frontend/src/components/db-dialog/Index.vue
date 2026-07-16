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
        <span
          v-if="showConfirm"
          v-bk-tooltips="confirmButtonDisableInfo?.tooltips">
          <BkButton
            class="mr-8"
            :disabled="confirmButtonDisableInfo?.disabled"
            :loading="confirmLoading"
            theme="primary"
            @click="handleConfirm">
            {{ confirmText || t('确定') }}
          </BkButton>
        </span>
        <BkButton
          :loading="cancelLoading"
          @click="handleCancle">
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
    cancelHandler?: () => Promise<unknown>;
    cancelText?: string;
    closeIcon?: boolean;
    confirmButtonDisableInfo?: {
      disabled: boolean;
      tooltips: {
        content: string;
        disabled: boolean;
      };
    };
    confirmHandler?: () => Promise<unknown>;
    confirmText?: string;
    quickClose?: boolean;
    renderDirective?: 'if' | 'show';
    showConfirm?: boolean;
    title?: string;
    width?: number | string;
  }

  interface Emits {
    (e: 'update:isShow', isShow: boolean): void;
    (e: 'close'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    cancelHandler: undefined,
    cancelText: '',
    closeIcon: true,
    confirmButtonDisableInfo: undefined,
    confirmHandler: undefined,
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

  const confirmLoading = ref(false);
  const cancelLoading = ref(false);

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
    isShow.value = false;
    emit('update:isShow', false);
    emit('close');
  };

  // 确定
  const handleConfirm = () => {
    if (props.confirmButtonDisableInfo?.disabled) {
      return;
    }
    if (props.confirmHandler) {
      confirmLoading.value = true;
      Promise.resolve(props.confirmHandler())
        .then(() => {
          close();
        })
        .finally(() => {
          confirmLoading.value = false;
        });
      return;
    }

    confirmLoading.value = true;
    const { submit } = getModelProvier();
    submit()
      .then(() => {
        close();
      })
      .finally(() => {
        confirmLoading.value = false;
      });
  };

  // 取消
  const handleCancle = () => {
    if (props.cancelHandler) {
      cancelLoading.value = true;
      return leaveConfirm()
        .then(() => props.cancelHandler!())
        .then(() => close())
        .finally(() => {
          cancelLoading.value = false;
        });
    }

    const { cancel } = getModelProvier();

    cancelLoading.value = true;
    return leaveConfirm()
      .then(() => cancel())
      .then(() => close())
      .finally(() => {
        cancelLoading.value = false;
      });
  };
</script>
