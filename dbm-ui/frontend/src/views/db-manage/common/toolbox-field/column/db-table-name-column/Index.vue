<template>
  <EditableColumn
    :field="field"
    :label="label"
    :min-width="200"
    :required="required"
    :rules="rules">
    <template
      v-if="showBatchEdit"
      #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :single="single"
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
        :max-data="single ? 1 : -1"
        :paste-fn="tagInputPasteFn"
        :placeholder="placeholder"
        @change="handleChange" />
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

  import { batchSplitRegex } from '@common/regex';

  import { Column } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    disabled?: boolean;
    field: string;
    label: string;
    placeholder: string;
    required?: boolean;
    rules: NonNullable<ComponentProps<typeof Column>['rules']>;
    showBatchEdit?: boolean;
    single?: boolean;
  }

  interface Emits {
    (e: 'batch-edit', value: string[]): void;
    (e: 'change'): void;
  }

  interface Slots {
    tip: VNode;
  }

  withDefaults(defineProps<Props>(), {
    disabled: false,
    required: true,
    showBatchEdit: true,
  });
  const emits = defineEmits<Emits>();

  const slots = defineSlots<Slots>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

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

  const handleChange = () => {
    emits('change');
  };

  const handleShowTips = () => {
    tippyIns?.show();
  };

  const tagInputPasteFn = (value: string) => value.split(batchSplitRegex).map((item) => ({ id: item }));

  onMounted(() => {
    nextTick(() => {
      if (slots.tip && rootRef.value !== null) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          appendTo: () => document.body,
          arrow: true,
          content: popRef.value,
          hideOnClick: true,
          interactive: true,
          maxWidth: 'none',
          offset: [0, 18],
          placement: 'top',
          theme: 'light',
          trigger: 'manual',
          zIndex: 9998,
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
