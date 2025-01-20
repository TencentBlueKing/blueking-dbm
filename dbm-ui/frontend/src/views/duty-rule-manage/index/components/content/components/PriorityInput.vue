<template>
  <BkLoading :loading="loading">
    <BkInput
      ref="inputRef"
      v-model="localValue"
      class="priority-input"
      :max="100"
      :min="1"
      placeholder="1～100"
      type="number"
      @blur="handleBlur"
      @keyup="handleEnter" />
  </BkLoading>
</template>
<script setup lang="ts">
  interface Props {
    loading?: boolean;
  }

  interface Emits {
    (e: 'submit', value: number): void;
  }

  withDefaults(defineProps<Props>(), {
    loading: false,
  });

  const emit = defineEmits<Emits>();

  const localValue = defineModel<number>({
    default: 1,
  });

  const inputRef = ref();
  let isEnterKey = false;

  const handleBlur = () => {
    if (isEnterKey) {
      isEnterKey = false;
      return;
    }
    emit('submit', localValue.value);
  };

  const handleEnter = (_: number, event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      isEnterKey = true;
      emit('submit', localValue.value);
    }
  };

  onMounted(() => {
    inputRef.value.focus();
  });
</script>
<style lang="less" scoped>
  .priority-input {
    :deep(.bk-input--number-control) {
      display: none;
    }
  }
</style>
