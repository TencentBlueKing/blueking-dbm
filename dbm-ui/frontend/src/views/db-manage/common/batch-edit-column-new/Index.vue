<template>
  <div
    ref="rootRef"
    v-bind="$attrs"
    @click.stop="">
    <BkButton
      v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
      text
      theme="primary"
      @click="handleShow">
      <DbIcon type="bulk-edit" />
    </BkButton>
  </div>
  <div style="display: none">
    <div
      ref="popRef"
      class="batch-edit-column-select-new">
      <div class="main-title">{{ t('统一设置') }}{{ label }}</div>
      <div
        v-if="mode === 'default'"
        class="title-spot mb-6"
        style="font-weight: normal">
        <span>{{ label }}</span> <span class="required" />
      </div>
      <slot />
      <div class="footer-box">
        <BkButton
          size="small"
          style="margin-left: auto"
          theme="primary"
          @click="handleConfirm">
          {{ t('确认') }}
        </BkButton>
        <BkButton
          class="ml-8"
          size="small"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
  import tippy, { type Instance, type Props as TippyProps, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  // import BatchEditDatePick from './edit/DatePicker.vue';
  // import BatchEditInput from './edit/Input.vue';
  import BatchEditNumberInput from './edit/NumberInput.vue';
  import BatchEditSelect from './edit/Select.vue';
  import BatchEditTagInput from './edit/TagInput.vue';
  import BatchEditTextarea from './edit/Textarea.vue';

  interface Props {
    cancelHandler?: () => Promise<any> | void;
    confirmHandler: () => Promise<any> | void;
    label: string;
    mode?: 'default' | 'custom';
  }

  let tippyInstance: Instance | undefined;

  const createTippy = (target: SingleTarget, options: TippyProps) => {
    if (!tippyInstance) {
      tippyInstance = tippy(target, options);
    }
  };
  export {
    // BatchEditDatePick,
    // BatchEditInput,
    BatchEditNumberInput,
    BatchEditSelect,
    BatchEditTagInput,
    BatchEditTextarea,
  };
</script>
<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    cancelHandler: () => Promise.resolve(),
    mode: 'default',
  });

  const { t } = useI18n();

  const rootRef = useTemplateRef('rootRef');
  const popRef = useTemplateRef('popRef');

  const getTippyOptions = (): TippyProps => ({
    appendTo: () => document.body,
    arrow: true,
    content: popRef.value,
    hideOnClick: false,
    interactive: true,
    maxWidth: 'none',
    offset: [0, 12],
    placement: 'top-start',
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
    theme: 'light batch-edit-column-theme',
    trigger: 'click',
    zIndex: 999,
  });

  const handleShow = () => {
    destroyTippy();
    const tippyTarget = rootRef.value!.children[0];
    if (tippyTarget) {
      createTippy(tippyTarget as SingleTarget, getTippyOptions());
      tippyInstance!.show();
    }
  };

  const handleConfirm = () => {
    // tag-input 组件内为200ms后失焦处理失焦的回调，这里将任务添加至失焦回调后，以获取最新值
    setTimeout(() => {
      Promise.resolve()
        .then(() => props.confirmHandler())
        .then(() => {
          tippyInstance!.hide();
        });
    }, 210);
  };

  const handleCancel = () => {
    Promise.resolve()
      .then(() => props.cancelHandler())
      .then(() => {
        tippyInstance!.hide();
      });
  };

  const destroyTippy = () => {
    if (tippyInstance) {
      tippyInstance.hide();
      tippyInstance.unmount();
      tippyInstance.destroy();
      tippyInstance = undefined;
    }
  };

  onBeforeUnmount(() => {
    destroyTippy();
  });
</script>

<style lang="less">
  .batch-edit-column-select-new {
    width: 395px;

    .main-title {
      margin-bottom: 20px;
      font-size: 16px;
      color: #313238;
    }

    .footer-box {
      margin-top: 30px;
      text-align: end;

      button {
        width: 60px;
      }
    }
  }

  .tippy-box[data-theme~='batch-edit-column-theme'] {
    padding: 16px;
    background-color: #fff;
    border: 1px solid #dcdee5 !important;
    border-radius: 4px !important;
    box-shadow: 0 0 6px 0 #dcdee5 !important;

    .tippy-content {
      padding: 0;
      background-color: #fff;
    }
  }
</style>
