<template>
  <div>
    <component
      :is="renderCom"
      :is-error="isError" />
  </div>
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
  import Qdrant from './Qdrant.vue';
  import Redis from './Redis.vue';
  import Riak from './Riak.vue';
  import SqlServer from './SqlServer.vue';
  import SurrealDB from './SurrealDB.vue';
  import TendbCluster from './TendbCluster.vue';
  import VictoriaMetrics from './VictoriaMetrics.vue';

  interface Props {
    isError: boolean;
    name: string;
  }

  const props = defineProps<Props>();

  const comMap = {
    [DBTypes.DORIS]: Doris,
    [DBTypes.ES]: Es,
    [DBTypes.HDFS]: Hdfs,
    [DBTypes.INFLUXDB]: Influxdb,
    [DBTypes.K8S_QDRANT]: Qdrant,
    [DBTypes.K8S_SURREALDB]: SurrealDB,
    [DBTypes.K8S_VICTORIAMETRICS]: VictoriaMetrics,
    [DBTypes.KAFKA]: Kafka,
    [DBTypes.MONGODB]: MongoDB,
    [DBTypes.MYSQL]: Mysql,
    [DBTypes.ORACLE]: Oracle,
    [DBTypes.PULSAR]: Pulsar,
    [DBTypes.REDIS]: Redis,
    [DBTypes.RIAK]: Riak,
    [DBTypes.SQLSERVER]: SqlServer,
    [DBTypes.TENDBCLUSTER]: TendbCluster,
  };

  const renderCom = computed(() => comMap[props.name as keyof typeof comMap]);
</script>
