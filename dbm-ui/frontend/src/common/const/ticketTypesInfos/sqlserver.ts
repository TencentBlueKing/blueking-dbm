import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { TicketTypes } from '../ticketTypes';

export const sqlServerType = {
  [TicketTypes.SQLSERVER_HA_APPLY]: {
    dbType: DBTypes.SQLSERVER,
    id: TicketTypes.SQLSERVER_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.SQLSERVER_HA,
  },
  [TicketTypes.SQLSERVER_SINGLE_APPLY]: {
    dbType: DBTypes.SQLSERVER,
    id: TicketTypes.SQLSERVER_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.SQLSERVER_SINGLE,
  },
};

export type SqlServerTypeString = keyof typeof sqlServerType;
