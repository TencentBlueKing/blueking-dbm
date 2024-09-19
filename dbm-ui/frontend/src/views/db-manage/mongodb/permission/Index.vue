<template>
  <PermissionList :account-type="AccountTypes.MONGODB" />
</template>

<script setup lang="ts">
  import { AccountTypes } from '@common/const';

  import PermissionList from '@views/db-manage/common/permission/Index.vue';
</script>
