<template>
  <BkPopConfirm
    trigger="click"
    width="330"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="dumper-batch-edit-common mb-12">
        <div class="main-title mb-12">
          {{ t('批量编辑') }}
        </div>
        <div
          class="title-spot edit-title"
          style="font-weight: normal;">
          {{ config.title }} <span class="required" />
        </div>
        <BkInput
          v-if="isShowInput"
          v-model="localValue"
          class="input-box"
          :min="1"
          :placeholder="config.placeholder"
          :type="config.type" />
        <MultipleInput
          v-if="config.type === 'textarea'"
          ref="multipleInputRef" />
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MultipleInput from './MultipleInput.vue';

  interface Props {
    config: {
      type: 'text' | 'number' | 'password' | 'textarea' | string
      title: string,
      placeholder: string,
    }
  }

  interface Emits {
    (e: 'data-change', value: string[], isBatch: boolean): void,
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const multipleInputRef = ref();
  const localValue = ref('');

  const isShowInput = computed(() => ['text', 'number', 'password'].includes(props.config.type));

  const handleConfirm = () => {
    if (props.config.type === 'textarea') {
      const data = multipleInputRef.value.getValue();
      if (data.length > 0) {
        emits('data-change', data, true);
      }
    } else {
      emits('data-change', [localValue.value], false);
    }
    localValue.value = '';
  };
</script>

<style lang="less">
.dumper-batch-edit-common {
  & + .bk-pop-confirm-footer {
    button {
      width: 72px;
    }
  }
  .main-title {
    font-weight: 700;
    font-size: 12px;
    color: #63656E;
  }
  .edit-title {
    margin-bottom: 6px;
  }

  .input-box {
    height: 32px;
  }
}
</style>
