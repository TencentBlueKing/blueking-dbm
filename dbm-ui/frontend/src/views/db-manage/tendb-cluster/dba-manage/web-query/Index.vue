<template>
  <WebQuery :db-type="DBTypes.TENDBCLUSTER" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebQuery from '@views/db-manage/common/web-query/Index.vue';
</script>
