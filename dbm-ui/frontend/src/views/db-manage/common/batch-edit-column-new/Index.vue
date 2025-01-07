<template>
  <BkPopConfirm
    :is-show="isShow"
    trigger="manual"
    width="395"
    @cancel="() => (isShow = false)"
    @confirm="handleConfirm">
    <BkButton
      v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
      text
      theme="primary"
      @click="handleShow">
      <DbIcon type="bulk-edit" />
    </BkButton>
    <template #content>
      <div class="batch-edit-column-select-new">
        <div class="main-title">{{ t('统一设置') }}{{ label }}</div>
        <div
          class="title-spot mb-6"
          style="font-weight: normal">
          <span>{{ label }}</span> <span class="required" />
        </div>
        <slot />
      </div>
    </template>
  </BkPopConfirm>
</template>

<script lang="ts">
  import type { InjectionKey } from 'vue';
  import { useI18n } from 'vue-i18n';

  // import BatchEditDatePick from './edit/DatePicker.vue';
  // import BatchEditInput from './edit/Input.vue';
  import BatchEditNumberInput from './edit/NumberInput.vue';
  import BatchEditSelect from './edit/Select.vue';
  import BatchEditTagInput from './edit/TagInput.vue';
  // import BatchEditTextarea from './edit/Textarea.vue';

  interface Props {
    label: string;
  }

  type Emits = (e: 'confirm') => void;

  export const BatchEditColumnInjectKey: InjectionKey<{
    addType: (type: string) => void;
    deleteType: (type: string) => void;
  }> = Symbol.for('batch-edit-column');

  export {
    // BatchEditDatePick,
    // BatchEditInput,
    BatchEditNumberInput,
    BatchEditSelect,
    BatchEditTagInput,
    // BatchEditTextarea,
  };
</script>
<script setup lang="ts">
  withDefaults(defineProps<Props>(), {});

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShow = ref(false);

  const typeSet = new Set<string>();

  const handleShow = () => {
    if (!isShow.value) {
      isShow.value = true;
    }
  };

  const handleConfirm = () => {
    if (typeSet.has('tag-input')) {
      // 组件内为200ms后失焦处理失焦的回调，这里将任务添加至失焦回调后，以获取最新值
      setTimeout(() => {
        handleConfirmChange();
      }, 210);
    } else {
      handleConfirmChange();
    }
  };

  const handleConfirmChange = () => {
    emits('confirm');
    isShow.value = false;
  };

  const addType = (type: string) => {
    typeSet.add(type);
  };

  const deleteType = (type: string) => {
    typeSet.delete(type);
  };

  provide(BatchEditColumnInjectKey, {
    addType,
    deleteType,
  });
</script>

<style lang="less">
  .batch-edit-column-select-new {
    margin-bottom: 30px;

    & + .bk-pop-confirm-footer {
      button {
        width: 60px;
      }
    }

    .main-title {
      margin-bottom: 20px;
      font-size: 16px;
      color: #313238;
    }
  }
</style>
