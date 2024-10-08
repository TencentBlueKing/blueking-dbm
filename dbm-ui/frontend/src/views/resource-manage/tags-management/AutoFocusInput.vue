<template>
  <BkInput
    ref="inputRef"
    v-bind="attrs"
    :clearable="clearable"
    :model-value="modelValue"
    @blur="handleBlur" />
</template>

<script lang="tsx">
  import type { InputType } from 'bkui-vue/lib/input/input';
  import { defineComponent, onMounted, ref, useAttrs } from 'vue';

  export default defineComponent({
    name: 'AutoFocusInput',
    props: {
      modelValue: String,
      clearable: Boolean,
    },
    emits: ['blur'],
    setup(_, { emit }) {
      const attrs = useAttrs() as InputType;
      const inputRef = ref<HTMLInputElement | null>(null);

      const handleBlur = () => {
        emit('blur');
      };

      onMounted(() => {
        inputRef.value?.focus();
      });

      return {
        attrs,
        inputRef,
        handleBlur,
      };
    },
  });
</script>
