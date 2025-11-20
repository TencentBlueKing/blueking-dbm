import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { TicketTypes } from '../ticketTypes';

export const redisType = {
  [TicketTypes.REDIS_CLUSTER_APPLY]: {
    dbType: DBTypes.REDIS,
    id: TicketTypes.REDIS_CLUSTER_APPLY,
    name: t('Redis集群部署'),
    type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
  },
  [TicketTypes.REDIS_INS_APPLY]: {
    dbType: DBTypes.REDIS,
    id: TicketTypes.REDIS_INS_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.REDIS_INSTANCE,
  },
};
