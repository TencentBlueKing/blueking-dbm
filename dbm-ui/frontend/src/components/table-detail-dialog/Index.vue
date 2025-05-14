<template>
  <Teleport to=".navigation-container">
    <div
      v-show="modelValue"
      ref="rootRef"
      class="dbm-table-detail-dialog">
      <div class="dbm-table-detail-dialog-content">
        <slot />
      </div>
      <div
        class="dbm-table-detail-dialog-close"
        @click="handleClose">
        <DbIcon type="close" />
      </div>
      <div
        v-bk-tooltips="t('向左展开')"
        class="dbm-table-detail-dialog-expand-max"
        @click="handleExpandMax">
        <DbIcon type="2-jiantou-zuo" />
      </div>
      <div
        ref="resizeHandleRef"
        class="dbm-table-detail-dialog-resize" />
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { onBeforeRouteLeave, useRoute } from 'vue-router';

  import useResize from './hooks/use-resize';

  interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    defaultOffsetLeft?: number;
    // eslint-disable-next-line vue/no-unused-properties
    minWidth?: number;
  }

  type Emits = (e: 'close') => void;

  withDefaults(defineProps<Props>(), {
    defaultOffsetLeft: 0,
    minWidth: 600,
  });

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<boolean>({
    default: false,
  });

  const route = useRoute();

  const { t } = useI18n();

  let isRouteChange = false;

  const rootRef = useTemplateRef('rootRef');
  const resizeHandleRef = useTemplateRef('resizeHandleRef');

  useResize(rootRef, resizeHandleRef);

  watch(route, () => {
    console.log('route = ', route);
  });

  const handleClose = () => {
    modelValue.value = false;
    emits('close');
  };

  const handleExpandMax = () => {
    rootRef.value!.style.width = '90%';
  };

  const handleClickClose = (event: Event) => {
    if (!modelValue.value) {
      return;
    }

    const eventPath = event.composedPath() as HTMLElement[];

    for (const ele of eventPath) {
      if (
        ele.classList?.contains('bk-modal') ||
        ele.classList?.contains('dbm-table-detail-dialog') ||
        ele.classList?.contains('bk-popper') ||
        ele.classList?.contains('tippy-box')
      ) {
        return true;
      }
    }

    if (!isRouteChange) {
      handleClose();
    }
  };

  onBeforeRouteLeave(() => {
    isRouteChange = true;
  });

  onMounted(() => {
    document.body.addEventListener('click', handleClickClose);
  });

  onBeforeUnmount(() => {
    document.body.removeEventListener('click', handleClickClose);
  });
</script>
<style lang="less">
  .dbm-table-detail-dialog {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 999;
    display: block;
    width: 60%;
    max-width: 90%;
    min-width: 300px;
    background: #fff;
    box-shadow: -2px 0 6px 0 #0000001a;
  }

  .dbm-table-detail-dialog-content {
    height: 100%;
    overflow: hidden;
    transform: scale(1);
  }

  .dbm-table-detail-dialog-close {
    position: absolute;
    top: 12px;
    right: 12px;
    display: flex;
    width: 32px;
    height: 32px;
    font-size: 24px;
    color: #979ba5;
    cursor: pointer;
    background: #dcdee5;
    border-radius: 2px;
    justify-content: center;
    align-items: center;

    &:hover {
      background: #c4c6cc;
    }
  }

  .dbm-table-detail-dialog-expand-max {
    position: absolute;
    top: 50%;
    left: -16px;
    display: flex;
    width: 16px;
    height: 64px;
    color: #fff;
    cursor: pointer;
    background: #dcdee5;
    border-radius: 4px 0 0 4px;
    transform: translateY(-50%);
    align-items: center;
    justify-content: center;
    transition: all 0.15s;

    &:hover {
      color: #fff;
      background: #3a84ff;
    }
  }

  .dbm-table-detail-dialog-resize {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    display: flex;
    width: 8px;
    cursor: col-resize;
    border-left: 2px solid transparent;
    transition: all 0.15s;
    justify-content: flex-end;
    align-items: center;

    &:hover {
      border-color: #3a84ff;
    }

    &::after {
      position: absolute;
      width: 2px;
      height: 2px;
      color: #c4c6cc;
      background: currentcolor;
      content: '';
      box-shadow:
        0 4px 0 0 currentcolor,
        0 8px 0 0 currentcolor,
        0 -4px 0 0 currentcolor,
        0 -8px 0 0 currentcolor;
    }
  }
</style>
