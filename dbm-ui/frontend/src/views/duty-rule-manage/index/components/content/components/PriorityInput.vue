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
    requestHandler: (value: number) => Promise<void>;
  }

  const props = defineProps<Props>();

  const localValue = defineModel<number>({
    default: 1,
  });

  const inputRef = ref();
  const loading = ref(false);
  let isEnterKey = false;

  const updatePriority = async () => {
    loading.value = true;
    try {
      await props.requestHandler(localValue.value);
    } finally {
      loading.value = false;
    }
  };

  const handleBlur = () => {
    if (isEnterKey) {
      isEnterKey = false;
      return;
    }
    updatePriority();
  };

  const handleEnter = (_: number, event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      isEnterKey = true;
      updatePriority();
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
