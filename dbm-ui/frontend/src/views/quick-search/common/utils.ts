type groupByDbTypeArray<T> = Array<{
  dbType: string;
  dataList: T;
}>;

export const groupByDbType = <
  T extends {
    db_type: string;
    bk_biz_id: number;
  },
>(
  data: Array<T>,
) => {
  const bizMap: Record<string, Set<number>> = {};
  const clusterMap: Record<string, Array<T>> = {};

  data.forEach((clusterItem) => {
    const { db_type: dbType, bk_biz_id: bizId } = clusterItem;

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
    dataList: Object.keys(clusterMap).reduce(
      (prevArr, mapKey) => [
        ...prevArr,
        {
          dbType: mapKey,
          dataList: clusterMap[mapKey],
        },
      ],
      [] as groupByDbTypeArray<Array<T>>,
    ),
    bizMap,
  };
};
