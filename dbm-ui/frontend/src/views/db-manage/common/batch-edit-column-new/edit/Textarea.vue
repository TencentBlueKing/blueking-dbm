<template>
  <BkInput
    ref="textareaRef"
    v-model="modelValue"
    class="batch-edit-column-textarea"
    :rows="5"
    v-bind="attrs"
    type="textarea" />
</template>
<script setup lang="ts">
  const modelValue = defineModel<string>();

  const attrs = useAttrs();

  const textareaRef = useTemplateRef('textareaRef');

  onMounted(() => {
    nextTick(() => {
      textareaRef.value!.focus();
    });
  });
</script>
<style lang="less">
  .batch-edit-column-textarea {
    .bk-textarea {
      resize: none;
    }
  }
</style>
