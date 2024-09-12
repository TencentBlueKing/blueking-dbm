<template>
  <WebConsole :db-type="DBTypes.TENDBCLUSTER" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebConsole from '@components/webconsole/Index.vue';
</script>
