import { DBTypes, type TicketTypes } from '@common/const';

export function useToolboxRoute(dbType: DBTypes) {
  const dbToolbox = dbType === DBTypes.TENDBCLUSTER ? 'tendb-cluster' : dbType;

  const createRouteItem = (ticketType: TicketTypes, navName: string) => ({
    name: ticketType,
    path: `${ticketType}/:page?`,
    meta: {
      navName,
      fullscreen: true,
    },
    component: () => import(`@views/db-manage/${dbToolbox}/${ticketType}/Index.vue`),
  });

  return {
    createRouteItem,
  };
}
