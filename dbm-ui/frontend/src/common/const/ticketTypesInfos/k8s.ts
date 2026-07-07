import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { TicketTypes } from '../ticketTypes';

export const k8sType = {
  [TicketTypes.K8S_QDRANT_HA_APPLY]: {
    id: TicketTypes.K8S_QDRANT_HA_APPLY,
    name: t('Qdrant 集群部署'),
    type: ClusterTypes.K8S_QDRANT_HA,
  },
  [TicketTypes.K8S_SURREALDB_HA_APPLY]: {
    id: TicketTypes.K8S_SURREALDB_HA_APPLY,
    name: t('SurrealDB 集群部署'),
    type: ClusterTypes.K8S_SURREALDB_HA,
  },
  [TicketTypes.K8S_SURREALDB_SINGLE_APPLY]: {
    id: TicketTypes.K8S_SURREALDB_SINGLE_APPLY,
    name: t('SurrealDB 单节点部署'),
    type: ClusterTypes.K8S_SURREALDB_SINGLE,
  },
};
