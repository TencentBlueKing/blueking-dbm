import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { bigdata } from './bigdata';
import { mongodb } from './mongodb';
import { mysql } from './mysql';
import { redis } from './redis';
import { spider } from './spider';
import { sqlserver } from './sqlserver';

export interface ClusterTypeInfoItem {
  dbType: DBTypes;
  id: ClusterTypes;
  machineList: {
    id: MachineTypes;
    name: string;
  }[];
  moduleId: ExtractedControllerDataKeys;
  name: string;
  specClusterName: string; // 规格对应的集群名，磨平集群类型差异
}

export type InfoType = {
  [x in ClusterTypes]?: ClusterTypeInfoItem;
};

export type RequiredInfoType = {
  [x in ClusterTypes]: ClusterTypeInfoItem;
};

/**
 * 集群类型对应配置
 */
export const clusterTypeInfos: RequiredInfoType = {
  ...bigdata,
  ...mongodb,
  ...mysql,
  ...redis,
  ...spider,
  ...sqlserver,
} as RequiredInfoType;
export type ClusterTypeInfos = keyof typeof clusterTypeInfos;
