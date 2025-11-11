<template>
  <RouterView />
  <DbaHelper />
</template>
<script setup lang="ts">
  import DbaHelper from '@views/db-manage/common/DbaHelper.vue';
</script>
