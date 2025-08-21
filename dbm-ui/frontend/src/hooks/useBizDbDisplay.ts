/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import { useRequest } from 'vue-request';

import type { BigdataFunctions } from '@services/model/function-controller/functionController';
import { queryClusterInstanceCount } from '@services/source/dbbase';

import { useFunController, useUserProfile } from '@stores';

import { ClusterTypes, type DBInfoItem, DBTypeInfos, DBTypes, UserPersonalSettings } from '@common/const';

export function useBizDbDisplay() {
  const funControllerStore = useFunController();
  const userProfileStore = useUserProfile();

  const tabList = ref<DBInfoItem[]>([]);
  const catchError = ref(false);

  const isError = computed(() => !!clusterInstanceError.value || catchError.value);

  const {
    data: clusterInstanceCount,
    error: clusterInstanceError,
    loading: isLoading,
  } = useRequest(queryClusterInstanceCount, {
    defaultParams: [
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      },
    ],
  });

  watch(
    [clusterInstanceCount, () => userProfileStore.profile],
    () => {
      catchError.value = false;
      let finalTabList = Object.values(DBTypeInfos);

      if (!clusterInstanceCount.value) {
        tabList.value = finalTabList;
        return;
      }

      const countKeyMap: Record<string, string[]> = {
        [DBTypes.MONGODB]: [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
        [DBTypes.MYSQL]: [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA],
        [DBTypes.ORACLE]: [ClusterTypes.ORACLE_PRIMARY_STANDBY, ClusterTypes.ORACLE_SINGLE_NONE],
        [DBTypes.REDIS]: [ClusterTypes.REDIS_INSTANCE, 'redis_cluster'],
        [DBTypes.SQLSERVER]: [ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.SQLSERVER_HA],
        [DBTypes.TENDBCLUSTER]: [ClusterTypes.TENDBCLUSTER],
      };

      try {
        const resultList = Object.keys(DBTypeInfos).reduce<DBInfoItem[]>((prevList, dbType) => {
          const dbTypeInfo = DBTypeInfos[dbType as DBTypes];

          if (dbTypeInfo) {
            if (dbTypeInfo.moduleId === 'bigdata') {
              const data = funControllerStore.funControllerData.getFlatData(dbTypeInfo.moduleId);
              const clusterCount =
                clusterInstanceCount.value![dbTypeInfo.id as unknown as ClusterTypes].cluster_count || 0;
              if (data[dbType as BigdataFunctions] && clusterCount) {
                return prevList.concat(dbTypeInfo);
              }
            } else {
              const controllerData = funControllerStore.funControllerData.getFlatData(dbTypeInfo.moduleId);
              const clusterCount = countKeyMap[dbTypeInfo.id as string].reduce(
                (prevCount, key) => prevCount + (clusterInstanceCount.value![key as ClusterTypes]?.cluster_count || 0),
                0,
              );
              if (controllerData[dbTypeInfo.moduleId] && clusterCount) {
                return prevList.concat(dbTypeInfo);
              }
            }
          }
          return prevList;
        }, []);

        const topDbTypes: string[] = userProfileStore.profile[UserPersonalSettings.TOP_DB_TYPES] || [];
        if (topDbTypes.length > 0) {
          const resultMap = Object.fromEntries(resultList.map((resultItem) => [resultItem.id, resultItem]));
          const topList = topDbTypes.reduce<DBInfoItem[]>((prevList, topItem) => {
            if (resultMap[topItem]) {
              return prevList.concat(resultMap[topItem]);
            }
            return prevList;
          }, []);

          const commonList = resultList.filter((resultItem) => !topDbTypes.includes(resultItem.id));

          finalTabList = topList.concat(commonList);
        } else {
          finalTabList = resultList;
        }
      } catch (err) {
        catchError.value = true;
        console.log(err);
      }

      tabList.value = finalTabList;
    },
    {
      immediate: true,
    },
  );

  return {
    isError,
    isLoading,
    tabList,
  };
}
