<template>
  <EditableColumn
    :field="field"
    :label="label"
    :min-width="200"
    :required="required"
    :rules="rules">
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :title="label"
        type="taginput"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-select-button"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <div
      ref="root"
      class="edit-table-name-content"
      @click="handleShowTips">
      <EditableTagInput
        v-model="modelValue"
        allow-auto-match
        allow-create
        clearable
        :disabled="disabled"
        has-delete-icon
        :placeholder="placeholder" />
      <div style="display: none">
        <div
          ref="pop"
          style="font-size: 12px; line-height: 24px; color: #63656e">
          <slot name="tip" />
        </div>
      </div>
    </div>
  </EditableColumn>
</template>

<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { type VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { Column as EditableColumn } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    label: string;
    field: string;
    placeholder: string;
    rules: NonNullable<ComponentProps<typeof EditableColumn>['rules']>;
    required?: boolean;
    disabled?: boolean;
  }

  interface Emits {
    (e: 'batch-edit', value: string[]): void;
  }

  interface Slots {
    tip: VNode;
  }

  withDefaults(defineProps<Props>(), {
    required: true,
    disabled: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const slots = defineSlots<Slots>();

  const { t } = useI18n();

  let tippyIns: Instance | undefined;

  const isShowBatchEdit = ref(false);
  const rootRef = useTemplateRef('root');
  const popRef = useTemplateRef('pop');

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string[]);
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    nextTick(() => {
      if (slots.tip && rootRef.value !== null) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          content: popRef.value,
          placement: 'top',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          trigger: 'manual',
          interactive: true,
          arrow: true,
          offset: [0, 18],
          zIndex: 9998,
          hideOnClick: true,
        });
      }
    });
  });

  onBeforeUnmount(() => {
    if (slots.tip && tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>

<style lang="less" scoped>
  .batch-select-button {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .edit-table-name-content {
    width: 100%;
  }
</style>
