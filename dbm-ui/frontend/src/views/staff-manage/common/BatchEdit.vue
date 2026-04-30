<template>
  <div
    ref="rootRef"
    v-bind="$attrs"
    @click.stop="">
    <BkButton
      v-bk-tooltips="{
        content: t('统一设置：将该列统一设置为相同的值'),
        disabled: disabled,
      }"
      :disabled="disabled"
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
        class="title-spot mb-6"
        style="font-weight: normal">
        <span>{{ label }}</span> <span class="required" />
      </div>
      <MemberSelector
        v-model="modelValue"
        :multiple="multiple" />
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

  import MemberSelector from '@components/db-member-selector/index.vue';

  interface Props {
    disabled?: boolean;
    field: string;
    label: string;
    multiple?: boolean;
  }

  type Emits = (e: 'batch-edit', value: string[], field: string) => void;

  let tippyInstance: Instance | undefined;

  const createTippy = (target: SingleTarget, options: TippyProps) => {
    if (!tippyInstance) {
      tippyInstance = tippy(target, options);
    }
  };
</script>
<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    multiple: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rootRef = useTemplateRef('rootRef');
  const popRef = useTemplateRef('popRef');

  const modelValue = ref<string[]>([]);

  const getTippyOptions = (): TippyProps => ({
    appendTo: () => document.body,
    arrow: true,
    content: popRef.value,
    hideOnClick: false,
    interactive: true,
    maxWidth: 'none',
    offset: [0, 12],
    onShow: () => {
      modelValue.value = [];
    },
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
    zIndex: 9999,
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
    setTimeout(() => {
      emits('batch-edit', modelValue.value, props.field);
      tippyInstance!.hide();
    }, 210);
  };

  const handleCancel = () => {
    tippyInstance!.hide();
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
