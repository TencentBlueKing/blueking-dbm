import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { TicketTypes } from '../ticketTypes';

export const mongoType = {
  [TicketTypes.MONGODB_REPLICASET_APPLY]: {
    id: TicketTypes.MONGODB_REPLICASET_APPLY,
    name: t('MongoDB副本集部署'),
    type: ClusterTypes.MONGO_REPLICA_SET,
  },
  [TicketTypes.MONGODB_SHARD_APPLY]: {
    id: TicketTypes.MONGODB_SHARD_APPLY,
    name: t('MongoDB分片集群部署'),
    type: ClusterTypes.MONGO_SHARED_CLUSTER,
  },
};
