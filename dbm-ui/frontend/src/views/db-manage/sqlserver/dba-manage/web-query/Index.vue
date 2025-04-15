<template>
  <WebQuery
    action-id="sqlserver_dbconsole"
    :db-type="DBTypes.SQLSERVER" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebQuery from '@views/db-manage/common/web-query/Index.vue';
</script>
