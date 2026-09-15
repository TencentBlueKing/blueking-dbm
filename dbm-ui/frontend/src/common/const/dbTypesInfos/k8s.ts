import { DBTypes } from '../dbTypes';

import { type DbInfoType } from './index';

export const k8s: DbInfoType = {
  [DBTypes.K8S_QDRANT]: {
    icon: 'cluster',
    id: DBTypes.K8S_QDRANT,
    machineList: [],
    moduleId: 'k8s',
    name: 'Qdrant',
    routeIndexName: 'QdrantManage',
  },
  [DBTypes.K8S_SURREALDB]: {
    icon: 'cluster',
    id: DBTypes.K8S_SURREALDB,
    machineList: [],
    moduleId: 'k8s',
    name: 'SurrealDB',
    routeIndexName: 'SurrealDBManage',
  },
};
