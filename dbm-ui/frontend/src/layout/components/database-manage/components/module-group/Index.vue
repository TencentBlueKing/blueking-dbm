<template>
  <component :is="renderCom" />
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import Es from './Es.vue';
  import Hdfs from './Hdfs.vue';
  import Influxdb from './Influxdb.vue';
  import Kafka from './Kafka.vue';
  import Mysql from './Mysql.vue';
  import Pulsar from './Pulsar.vue';
  import Redis from './Redis.vue';
  import Riak from './Riak.vue';
<<<<<<< HEAD
  import SqlServer from './SqlServer.vue';
=======
  import SQLServer from './Sqlserver.vue';
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
  import TendbCluster from './TendbCluster.vue';

  interface Props {
    name: string
  }

  const props = defineProps<Props>();

  const comMap = {
    es: Es,
    hdfs: Hdfs,
    influxdb: Influxdb,
    kafka: Kafka,
    mysql: Mysql,
    pulsar: Pulsar,
    redis: Redis,
    tendbCluster: TendbCluster,
    riak: Riak,
<<<<<<< HEAD
    sqlserver: SqlServer,
=======
    sqlserver: SQLServer,
>>>>>>> e04cfea7539447ae66957742c99b90edb58f0d2e
  };

  const renderCom = computed(() => comMap[props.name as keyof typeof comMap]);
</script>

