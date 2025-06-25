import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { bigdata } from './bigdata';
import { mongodb } from './mongodb';
import { mysql } from './mysql';
import { oracle } from './oracle';
import { redis } from './redis';
import { sqlserver } from './sqlserver';

interface ClusterTypeInfoItem {
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

type RequiredInfoType = {
  [x in ClusterTypes]: ClusterTypeInfoItem;
};

// 内部文件使用
export type ClusterTypeInfo = {
  [x in ClusterTypes]?: ClusterTypeInfoItem;
};

/**
 * 集群类型对应配置
 */
export const clusterTypeInfos = {
  ...bigdata,
  ...oracle,
  ...mongodb,
  ...mysql,
  ...redis,
  ...sqlserver,
} as RequiredInfoType;

export type ClusterTypeInfos = keyof typeof clusterTypeInfos;
