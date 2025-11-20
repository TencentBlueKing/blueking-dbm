import { DBTypes, type TicketTypes } from '@common/const';

export function createToolboxRoute(dbType: DBTypes) {
  const dbToolbox = dbType === DBTypes.TENDBCLUSTER ? 'tendb-cluster' : dbType;

  const createRouteItem = (
    ticketType: TicketTypes,
    navName: string,
    meta: { dbConsole?: string; fullscreen?: boolean; navName?: string } = {},
    options: { params?: string } = {},
  ) => ({
    component: () => import(`@views/db-manage/${dbToolbox}/${ticketType}/Index.vue`),
    meta: {
      fullscreen: true,
      navName,
      ticketType,
      ...meta,
    },
    name: ticketType,
    path: options.params ? `${ticketType}${options.params}` : `${ticketType}`,
  });

  return {
    createRouteItem,
  };
}
