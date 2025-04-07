<template>
  <WebQuery
    action-id="mysql_dbconsole"
    :db-type="DBTypes.MYSQL" />
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import WebQuery from '@views/db-manage/common/web-query/Index.vue';
</script>
