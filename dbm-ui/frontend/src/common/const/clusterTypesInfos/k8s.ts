import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';

import { type ClusterTypeInfo } from './index';

export const k8s: ClusterTypeInfo = {
  [ClusterTypes.K8S_QDRANT_HA]: {
    dbType: DBTypes.K8S_QRRANT,
    id: ClusterTypes.K8S_QDRANT_HA,
    listRouteName: 'QdrantHaList',
    machineList: [],
    moduleId: 'k8s',
    name: t('Qdrant 集群'),
    specClusterName: 'Qdrant',
  },
  [ClusterTypes.K8S_SURREALDB_HA]: {
    dbType: DBTypes.K8S_SURREALDB,
    id: ClusterTypes.K8S_SURREALDB_HA,
    listRouteName: 'SurrealdbHaList',
    machineList: [],
    moduleId: 'k8s',
    name: t('SurrealDB 集群'),
    specClusterName: 'SerrealDB',
  },
  [ClusterTypes.K8S_SURREALDB_SINGLE]: {
    dbType: DBTypes.K8S_SURREALDB,
    id: ClusterTypes.K8S_SURREALDB_SINGLE,
    listRouteName: 'SurrealdbSingleList',
    machineList: [],
    moduleId: 'k8s',
    name: t('SurrealDB 单节点'),
    specClusterName: 'SerrealDB',
  },
};
