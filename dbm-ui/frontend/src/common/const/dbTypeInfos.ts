import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { DBTypes } from './dbTypes';

interface InfoItem {
  id: DBTypes;
  name: string;
  moduleId: ExtractedControllerDataKeys;
}
type InfoType = {
  [x in DBTypes]?: InfoItem;
};
type RequiredInfoType = {
  [x in DBTypes]: InfoItem;
};

const mysql: InfoType = {
  [DBTypes.MYSQL]: {
    id: DBTypes.MYSQL,
    name: 'MySQL',
    moduleId: 'mysql',
  },
  [DBTypes.TENDBCLUSTER]: {
    id: DBTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
    moduleId: 'mysql',
  },
};
const redis: InfoType = {
  [DBTypes.REDIS]: {
    id: DBTypes.REDIS,
    name: 'Redis',
    moduleId: 'redis',
  },
};
const mongo: InfoType = {
  [DBTypes.MONGODB]: {
    id: DBTypes.MONGODB,
    name: 'MongoDB',
    moduleId: 'mongodb',
  },
};
const sqlserver: InfoType = {
  [DBTypes.SQLSERVER]: {
    id: DBTypes.SQLSERVER,
    name: 'SQLServer',
    moduleId: 'sqlserver',
  },
};
const bigdata: InfoType = {
  [DBTypes.ES]: {
    id: DBTypes.ES,
    name: 'ElasticSearch',
    moduleId: 'bigdata',
  },
  [DBTypes.KAFKA]: {
    id: DBTypes.KAFKA,
    name: 'Kafka',
    moduleId: 'bigdata',
  },
  [DBTypes.HDFS]: {
    id: DBTypes.HDFS,
    name: 'HDFS',
    moduleId: 'bigdata',
  },
  [DBTypes.INFLUXDB]: {
    id: DBTypes.INFLUXDB,
    name: 'InfuxDB',
    moduleId: 'bigdata',
  },
  [DBTypes.RIAK]: {
    id: DBTypes.RIAK,
    name: 'Riak',
    moduleId: 'bigdata',
  },
  [DBTypes.PULSAR]: {
    id: DBTypes.PULSAR,
    name: 'Pulsar',
    moduleId: 'bigdata',
  },
  [DBTypes.DORIS]: {
    id: DBTypes.DORIS,
    name: 'Doris',
    moduleId: 'bigdata',
  },
};
export const DBTypeInfos = {
  ...mysql,
  ...redis,
  ...mongo,
  ...sqlserver,
  ...bigdata,
} as RequiredInfoType;
