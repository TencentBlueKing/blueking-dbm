import { DBTypes, type TicketTypes } from '@common/const';

export function createApplyRoute(
  dbType: DBTypes,
  ticketType: TicketTypes,
  navName: string,
  meta: { fullscreen?: boolean; navName?: string } = {},
) {
  const routeNameMap = {
    [DBTypes.ES]: 'elastic-search',
    [DBTypes.K8S_QRRANT]: 'qdrant',
    [DBTypes.K8S_SURREALDB]: 'surrealdb',
    [DBTypes.K8S_VICTORIAMETRICS]: 'victoriametrics',
    [DBTypes.TENDBCLUSTER]: 'tendb-cluster',
  };
  const dbToolbox = routeNameMap[dbType as keyof typeof routeNameMap] || dbType;

  return {
    component: () => import(`@views/db-manage/${dbToolbox}/${ticketType}/Index.vue`),
    meta: {
      dbType,
      fullscreen: false,
      navName,
      ticketType,
      ...meta,
    },
    name: ticketType,
    path: `${ticketType}`,
  };
}
