<template>
  <div>
    <p>Tab 键已被禁用。</p>
  </div>
</template>

<script setup lang="ts">
  const disableTabKey = (event: any) => {
    if (event.key === 'Tab') {
      event.preventDefault();
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', disableTabKey);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', disableTabKey);
  });
</script>
