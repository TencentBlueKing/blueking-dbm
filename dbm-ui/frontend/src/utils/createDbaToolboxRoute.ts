import { DBTypes, type TicketTypes } from '@common/const';

export function createDbaToolboxRoute(dbType: DBTypes) {
  const dbToolbox = dbType === DBTypes.TENDBCLUSTER ? 'tendb-cluster' : dbType;

  const createRouteItem = (
    ticketType: TicketTypes,
    navName: string,
    meta: { dbConsole?: string; fullscreen?: boolean; navName?: string; routeName?: string; tabName?: string } = {},
  ) => ({
    component: () => import(`@views/db-manage/${dbToolbox}/dba-manage/${ticketType}/Index.vue`),
    meta: {
      navName,
      routeName: ticketType,
      ...meta,
    },
    name: `DBA_${ticketType}`,
    path: `${ticketType}`,
  });

  return {
    createRouteItem,
  };
}
