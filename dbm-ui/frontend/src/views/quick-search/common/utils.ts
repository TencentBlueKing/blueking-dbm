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
