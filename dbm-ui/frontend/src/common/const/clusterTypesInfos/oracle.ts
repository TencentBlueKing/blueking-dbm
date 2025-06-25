import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';

import { type ClusterTypeInfo } from './index';

export const oracle: ClusterTypeInfo = {
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: {
    dbType: DBTypes.ORACLE,
    id: ClusterTypes.ORACLE_PRIMARY_STANDBY,
    machineList: [],
    moduleId: 'oracle',
    name: t('Oracle 主从'),
    specClusterName: 'Oracle',
  },
  [ClusterTypes.ORACLE_SINGLE_NONE]: {
    dbType: DBTypes.ORACLE,
    id: ClusterTypes.ORACLE_SINGLE_NONE,
    machineList: [],
    moduleId: 'oracle',
    name: t('Oracle 单节点'),
    specClusterName: 'Oracle',
  },
};
