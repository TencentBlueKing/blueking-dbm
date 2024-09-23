<template>
  <div class="operate-icon">
    <div
      class="operate-icon-inner"
      @click="handleClickFullScreen">
      <DbIcon
        class="operate-icon"
        :type="modelValue ? 'un-full-screen' : 'full-screen'" />
    </div>
  </div>
</template>
<script lang="ts" setup>
  interface Emits {
    (e: 'change'): void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<boolean>({
    default: false,
  });

  const handleClickFullScreen = () => {
    modelValue.value = !modelValue.value;
    emits('change');
  };
</script>
