import { DBTypes } from '../dbTypes';

import { type DbInfoType } from './index';

export const k8s: DbInfoType = {
  [DBTypes.K8S_QRRANT]: {
    id: DBTypes.K8S_QRRANT,
    machineList: [],
    moduleId: 'k8s',
    name: 'Qdrant',
    routeIndexName: 'QdrantManage',
  },
  [DBTypes.K8S_SURREALDB]: {
    id: DBTypes.K8S_SURREALDB,
    machineList: [],
    moduleId: 'k8s',
    name: 'SurrealDB',
    routeIndexName: 'SurrealDBManage',
  },
};
