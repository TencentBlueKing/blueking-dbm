<template>
  <RouterView :key="route.name" />
</template>
<script setup lang="ts">
  const route = useRoute();
</script>
