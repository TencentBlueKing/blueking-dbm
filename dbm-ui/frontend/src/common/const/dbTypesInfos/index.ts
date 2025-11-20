import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { bigdata } from './bigdata';
import { mongodb } from './mongodb';
import { mysql } from './mysql';
import { oracle } from './oracle';
import { redis } from './redis';
import { sqlserver } from './sqlserver';

export interface DBInfoItem {
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
} as RequiredInfoType;
