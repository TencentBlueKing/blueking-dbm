<template>
  <WebQuery
    action-id="tendbcluster_dbconsole"
    :db-type="DBTypes.TENDBCLUSTER" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebQuery from '@views/db-manage/common/web-query/Index.vue';
</script>
