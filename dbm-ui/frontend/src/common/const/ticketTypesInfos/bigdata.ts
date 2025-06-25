import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { TicketTypes } from '../ticketTypes';

export const bigDataType = {
  [TicketTypes.DORIS_APPLY]: {
    id: TicketTypes.DORIS_APPLY,
    name: t('Doris集群部署'),
    type: ClusterTypes.DORIS,
  },
  [TicketTypes.ES_APPLY]: {
    id: TicketTypes.ES_APPLY,
    name: t('ES集群部署'),
    type: ClusterTypes.ES,
  },
  [TicketTypes.HDFS_APPLY]: {
    id: TicketTypes.HDFS_APPLY,
    name: t('HDFS集群部署'),
    type: ClusterTypes.HDFS,
  },
  [TicketTypes.INFLUXDB_APPLY]: {
    id: TicketTypes.INFLUXDB_APPLY,
    name: t('InfluxDB集群部署'),
    type: ClusterTypes.INFLUXDB,
  },
  [TicketTypes.KAFKA_APPLY]: {
    id: TicketTypes.KAFKA_APPLY,
    name: t('Kafka集群部署'),
    type: ClusterTypes.KAFKA,
  },
  [TicketTypes.PULSAR_APPLY]: {
    id: TicketTypes.PULSAR_APPLY,
    name: t('Pulsar集群部署'),
    type: ClusterTypes.PULSAR,
  },
  [TicketTypes.RIAK_CLUSTER_APPLY]: {
    id: TicketTypes.RIAK_CLUSTER_APPLY,
    name: t('Riak集群部署'),
    type: ClusterTypes.RIAK,
  },
};
