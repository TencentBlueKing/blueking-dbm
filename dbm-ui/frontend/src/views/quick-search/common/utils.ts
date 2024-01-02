import { exportExcelFile } from '@utils';

import { t } from '@locales/index';

import type { FormatClusterArray } from './types';

export const formatCluster = <T extends {
  cluster_type: string
  bk_biz_id: number
}>(data: Array<T>) => {
  const bizMap: Record<string, Set<number>> = {};
  const clusterMap: Record<string, Array<T>> = {};

  data.forEach((clusterItem) => {
    const {
      cluster_type: clusterType,
      bk_biz_id: bizId,
    } = clusterItem;

    if (clusterMap[clusterType]) {
      clusterMap[clusterType].push(clusterItem);
    } else {
      clusterMap[clusterType] = [clusterItem];
    }

    if (bizMap[clusterType]) {
      bizMap[clusterType].add(bizId);
    } else {
      bizMap[clusterType] = new Set([bizId]);
    }
  });

  return {
    dataList: Object.keys(clusterMap).reduce((prevArr, mapKey) => [...prevArr, {
      clusterType: mapKey,
      dataList: clusterMap[mapKey],
    }], [] as FormatClusterArray<Array<T>>),
    bizMap,
  };
};

export const exportClusterExcelFile = (clusterType: string, data: Array<{
    clusterId: number,
    clusterName: string,
    clusterAlias: string,
    clusterType :string,
    immuteDomain: string,
    majorVersion: string,
    region: string,
    disasterTolerancLevel: string
  }>) => {
  const formatData = data.map(dataItem => ({
    [t('集群ID')]: String(dataItem.clusterId),
    [t('集群名称')]: dataItem.clusterName,
    [t('集群别名')]: dataItem.clusterAlias,
    [t('集群类型')]: dataItem.clusterType,
    [t('主域名')]: dataItem.immuteDomain,
    [t('主版本')]: dataItem.majorVersion,
    [t('地域')]: dataItem.region,
    [t('容灾等级')]: dataItem.disasterTolerancLevel,
  }));
  const colsWidths = [
    { width: 10 },
    { width: 16 },
    { width: 16 },
    { width: 24 },
    { width: 24 },
    { width: 16 },
    { width: 10 },
    { width: 10 },
  ];

  exportExcelFile(formatData, colsWidths, clusterType, `${clusterType}.xlsx`);
};
