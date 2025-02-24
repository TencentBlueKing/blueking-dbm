type groupByDbTypeArray<T> = Array<{
  dataList: T;
  dbType: string;
}>;

export const groupByDbType = <
  T extends {
    bk_biz_id: number;
    db_type: string;
  },
>(
  data: Array<T>,
) => {
  const bizMap: Record<string, Set<number>> = {};
  const clusterMap: Record<string, Array<T>> = {};

  data.forEach((clusterItem) => {
    const { bk_biz_id: bizId, db_type: dbType } = clusterItem;

    if (clusterMap[dbType]) {
      clusterMap[dbType].push(clusterItem);
    } else {
      clusterMap[dbType] = [clusterItem];
    }

    if (bizMap[dbType]) {
      bizMap[dbType].add(bizId);
    } else {
      bizMap[dbType] = new Set([bizId]);
    }
  });

  return {
    bizMap,
    dataList: Object.keys(clusterMap).reduce(
      (prevArr, mapKey) => [
        ...prevArr,
        {
          dataList: clusterMap[mapKey],
          dbType: mapKey,
        },
      ],
      [] as groupByDbTypeArray<Array<T>>,
    ),
  };
};
