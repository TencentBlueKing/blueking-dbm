<template>
  <div class="operate-icon">
    <div
      class="operate-icon-inner"
      @click="handleClickFullScreen">
      <DbIcon
        class="operate-icon"
        :type="isFullScreen ? 'un-full-screen' : 'full-screen'" />
    </div>
  </div>
</template>
<script lang="ts" setup>
  interface Emits {
    (e: 'toggleFullScreen'): void;
  }

  const emits = defineEmits<Emits>();

  const isFullScreen = defineModel<boolean>('isFullScreen', {
    default: false,
  });

  const handleClickFullScreen = () => {
    isFullScreen.value = !isFullScreen.value;
    emits('toggleFullScreen');
  };
</script>
