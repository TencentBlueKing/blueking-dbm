import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { bigdata } from './bigdata';
import { k8s } from './k8s';
import { mongodb } from './mongodb';
import { mysql } from './mysql';
import { oracle } from './oracle';
import { redis } from './redis';
import { sqlserver } from './sqlserver';

interface ClusterTypeInfoItem {
  dbType: DBTypes;
  id: ClusterTypes;
  listRouteName: string;
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
  ...mysql,
  ...redis,
  ...bigdata,
  ...mongodb,
  ...sqlserver,
  ...oracle,
  ...k8s,
} as RequiredInfoType;

export type ClusterTypeInfos = keyof typeof clusterTypeInfos;

/**
 * redis 集群版对应架构类型
 */
export const clusterRedisTypeList = [
  ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
  ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
  ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE,
  ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
  ClusterTypes.PREDIXY_REDIS_CLUSTER,
];
