<template>
  <WebConsole :db-type="DBTypes.TENDBCLUSTER" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebConsole from '@views/db-manage/common/webconsole/Index.vue';
</script>
