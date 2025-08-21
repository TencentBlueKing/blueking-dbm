import { DBTypes, type TicketTypes } from '@common/const';

export function createToolboxRoute(dbType: DBTypes) {
  const dbToolbox = dbType === DBTypes.TENDBCLUSTER ? 'tendb-cluster' : dbType;

  const createRouteItem = (
    ticketType: TicketTypes,
    navName: string,
    meta: { dbConsole?: string; fullscreen?: boolean; navName?: string; routeName?: string } = {},
  ) => ({
    component: () => import(`@views/db-manage/${dbToolbox}/${ticketType}/Index.vue`),
    meta: {
      fullscreen: true,
      navName,
      routeName: ticketType,
      ...meta,
    },
    name: ticketType,
    path: `${ticketType}`,
  });

  return {
    createRouteItem,
  };
}
