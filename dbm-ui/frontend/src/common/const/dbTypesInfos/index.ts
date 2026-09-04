import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { bigdata } from './bigdata';
import { k8s } from './k8s';
import { mongodb } from './mongodb';
import { mysql } from './mysql';
import { oracle } from './oracle';
import { redis } from './redis';
import { sqlserver } from './sqlserver';

export interface DBInfoItem {
  icon: string;
  id: DBTypes;
  machineList: {
    label: string;
    value: MachineTypes;
  }[];
  moduleId: ExtractedControllerDataKeys;
  name: string;
  routeIndexName: string;
}

type RequiredInfoType = {
  [x in DBTypes]: DBInfoItem;
};

// 内部使用
export type DbInfoType = {
  [x in DBTypes]?: DBInfoItem;
};

export const DBTypeInfos = {
  ...mysql,
  ...redis,
  ...bigdata,
  ...mongodb,
  ...sqlserver,
  ...oracle,
  ...k8s,
} as RequiredInfoType;

const readExcludeDbTypeMap = Object.fromEntries(
  [DBTypes.INFLUXDB, DBTypes.K8S_SURREALDB, DBTypes.K8S_QRRANT, DBTypes.K8S_VICTORIAMETRICS].map((item) => [
    item,
    true,
  ]),
);
export const readResourceDbTypes = Object.values(DBTypeInfos)
  .filter((item) => !readExcludeDbTypeMap[item.id])
  .map((item) => ({
    label: item.name,
    value: item.id as string,
  }))
  .concat([
    {
      label: 'Vm',
      value: 'vm',
    },
  ]);

const editExcludeDbTypeMap = Object.fromEntries(
  [DBTypes.INFLUXDB, DBTypes.TENDBCLUSTER, DBTypes.K8S_SURREALDB, DBTypes.K8S_QRRANT, DBTypes.K8S_VICTORIAMETRICS].map(
    (item) => [item, true],
  ),
);
export const editResourceDbTypes = Object.values(DBTypeInfos)
  .filter((item) => !editExcludeDbTypeMap[item.id])
  .map((item) => ({
    label: item.name,
    value: item.id as string,
  }))
  .concat([
    {
      label: 'Vm',
      value: 'vm',
    },
  ]);
