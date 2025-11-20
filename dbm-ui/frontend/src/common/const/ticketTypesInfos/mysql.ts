import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { TicketTypes } from '../ticketTypes';

export const mysqlType = {
  [TicketTypes.MYSQL_HA_APPLY]: {
    dbType: DBTypes.MYSQL,
    id: TicketTypes.MYSQL_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.TENDBHA,
  },
  [TicketTypes.MYSQL_SINGLE_APPLY]: {
    dbType: DBTypes.MYSQL,
    id: TicketTypes.MYSQL_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.TENDBSINGLE,
  },
  [TicketTypes.TENDBCLUSTER_APPLY]: {
    dbType: DBTypes.MYSQL,
    id: TicketTypes.TENDBCLUSTER_APPLY,
    name: t('TendbCluster分布式集群部署'),
    type: ClusterTypes.TENDBCLUSTER,
  },
};

export type MysqlTypeString = keyof typeof mysqlType;
