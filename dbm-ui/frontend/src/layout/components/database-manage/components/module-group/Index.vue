<template>
  <component :is="renderCom" />
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import { DBTypes } from '@common/const';

  import Doris from './Doris.vue';
  import Es from './Es.vue';
  import Hdfs from './Hdfs.vue';
  import Influxdb from './Influxdb.vue';
  import Kafka from './Kafka.vue';
  import MongoDB from './MongoDB.vue';
  import Mysql from './Mysql.vue';
  import Oracle from './Oracle.vue';
  import Pulsar from './Pulsar.vue';
  import Redis from './Redis.vue';
  import Riak from './Riak.vue';
  import SqlServer from './SqlServer.vue';
  import TendbCluster from './TendbCluster.vue';

  interface Props {
    name: string;
  }

  const props = defineProps<Props>();

  const comMap = {
    [DBTypes.DORIS]: Doris,
    [DBTypes.ES]: Es,
    [DBTypes.HDFS]: Hdfs,
    [DBTypes.INFLUXDB]: Influxdb,
    [DBTypes.KAFKA]: Kafka,
    [DBTypes.MONGODB]: MongoDB,
    [DBTypes.MYSQL]: Mysql,
    [DBTypes.PULSAR]: Pulsar,
    [DBTypes.REDIS]: Redis,
    [DBTypes.RIAK]: Riak,
    [DBTypes.SQLSERVER]: SqlServer,
    [DBTypes.TENDBCLUSTER]: TendbCluster,
    oracle: Oracle,
  };

  const renderCom = computed(() => comMap[props.name as keyof typeof comMap]);
</script>
