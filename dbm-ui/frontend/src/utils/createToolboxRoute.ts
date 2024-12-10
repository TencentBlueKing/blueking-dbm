import { DBTypes, type TicketTypes } from '@common/const';

export function createToolboxRoute(dbType: DBTypes) {
  const dbToolbox = dbType === DBTypes.TENDBCLUSTER ? 'tendb-cluster' : dbType;

  const createRouteItem = (
    ticketType: TicketTypes,
    navName: string,
    meta: { navName?: string; fullscreen?: boolean; dbConsole?: string } = {},
  ) => ({
    name: ticketType,
    path: `${ticketType}/:page?`,
    meta: {
      navName,
      fullscreen: true,
      ...meta,
    },
    component: () => import(`@views/db-manage/${dbToolbox}/${ticketType}/Index.vue`),
  });

  return {
    createRouteItem,
  };
}
