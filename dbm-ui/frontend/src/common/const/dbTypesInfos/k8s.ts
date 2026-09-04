import { DBTypes } from '../dbTypes';

import { type DbInfoType } from './index';

export const k8s: DbInfoType = {
  [DBTypes.K8S_QRRANT]: {
    icon: 'cluster',
    id: DBTypes.K8S_QRRANT,
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
  [DBTypes.K8S_VICTORIAMETRICS]: {
    icon: 'cluster',
    id: DBTypes.K8S_VICTORIAMETRICS,
    machineList: [],
    moduleId: 'k8s',
    name: 'VictoriaMetrics',
    routeIndexName: 'VictoriaMetricsManage',
  },
};
