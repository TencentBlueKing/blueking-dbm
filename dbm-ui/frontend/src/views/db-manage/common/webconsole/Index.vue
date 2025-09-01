<template>
  <Component
    :is="comMap[dbType]"
    v-bind="props" />
</template>
<script lang="ts" setup>
  import { DBTypes } from '@common/const';
  import MysqlContent from './mysql/Index.vue';
  import RedisContent from './redis/Index.vue';
  import MongodbContent from './mongodb/Index.vue';
  import TendbclusterContent from './tendbcluster/Index.vue';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const comMap = {
    [DBTypes.MONGODB]: MongodbContent,
    [DBTypes.MYSQL]: MysqlContent,
    [DBTypes.REDIS]: RedisContent,
    [DBTypes.TENDBCLUSTER]: TendbclusterContent,
  } as Record<DBTypes, any>;
</script>
