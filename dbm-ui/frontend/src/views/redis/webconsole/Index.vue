<template>
  <WebConsole :db-type="DBTypes.REDIS" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebConsole from '@components/webconsole/Index.vue';
</script>
