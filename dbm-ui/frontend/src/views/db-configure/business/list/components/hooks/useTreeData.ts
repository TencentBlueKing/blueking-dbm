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

import type { SearchOption } from 'bkui-vue/lib/tree/props';
import type { Ref } from 'vue';

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';
import { getBigdataResourceTree } from '@services/source/bigdata';
import { getMongoDBResourceTree } from '@services/source/mongodb';
import { getMysqlResourceTree } from '@services/source/mysql';
import { getRedisResourceTree } from '@services/source/redis';
import { geSqlserverResourceTree } from '@services/source/sqlserver';

import { useGlobalBizs } from '@stores';

import {
  type ClusterTypeInfos,
  clusterTypeInfos,
  ClusterTypes,
  confLevelInfos,
  ConfLevels,
  TicketTypes,
} from '@common/const';

import type { TreeData, TreeState } from '../types';

/**
 * 处理拓扑树数据及操作
 */
export const useTreeData = (treeState: TreeState) => {
  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();

  const apiMap: Record<string, (params: any) => ReturnType<typeof getBigdataResourceTree>> = {
    bigdata: getBigdataResourceTree,
    mongodb: getMongoDBResourceTree,
    mysql: getMysqlResourceTree,
    redis: getRedisResourceTree,
    sqlserver: geSqlserverResourceTree,
    tendbcluster: getMysqlResourceTree,
  };

  const activeTreeNode = computed(() => treeState.activeNode);
  provide('treeNode', readonly(activeTreeNode));
  const clusterType = inject<Ref<string>>('activeTab');

  /**
   * 处理树节点 icon
   */
  const treePrefixIcon = (data: any, type: string) => (type === 'node_action' ? 'default' : null);

  /**
   * tree search
   */
  const treeSearchConfig = computed<SearchOption>(() => ({
    match: treeSearchMatch,
    resultType: 'tree',
    showChildNodes: false,
    value: treeState.search,
  }));
  const treeSearchMatch = (searchValue: string, value: string) => value.indexOf(searchValue) > -1;

  /**
   * selected tree node
   * @param node tree node
   */
  const handleSelectedTreeNode = (
    node: any,
    status: any,
    { __is_open: isOpen, __is_selected: isSelected }: { __is_open: boolean; __is_selected: boolean },
  ) => {
    // eslint-disable-next-line no-param-reassign
    treeState.activeNode = node;
    // eslint-disable-next-line no-param-reassign
    treeState.selected = node;
    if (!isOpen && !isSelected) {
      treeRef.value.setNodeOpened(node, true);
      treeRef.value.setSelect(node, true);
      return;
    }

    if (isOpen && !isSelected) {
      treeRef.value.setSelect(node, true);
      return;
    }

    if (isSelected) {
      treeRef.value.setNodeOpened(node, !isOpen);
    }
  };

  watch(
    () => treeState.activeNode,
    (node) => {
      if (node) {
        // set route query info
        router.replace({
          query: {
            parentId: (node as TreeData).parentId,
            treeId: (node as TreeData).treeId,
          },
        });
      }
    },
    { deep: true, immediate: true },
  );

  /**
   * selected default tree node
   */
  const treeRef = ref();
  const setDefaultNode = () => {
    const { data = [] } = treeRef.value.getData();
    const { treeId } = route.query;
    let node = data[0];
    if (treeId) {
      const treeNode = data.find((item: TreeData) => item.treeId === treeId);
      treeNode && (node = treeNode);
    }
    // eslint-disable-next-line no-param-reassign
    treeState.selected = node;
    // eslint-disable-next-line no-param-reassign
    [treeState.activeNode] = treeState.data;
  };

  /**
   * 获取拓扑树
   */
  const fetchBusinessTopoTree = (dbType: string) => {
    // eslint-disable-next-line no-param-reassign
    treeState.loading = true;
    apiMap[dbType]({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_type: clusterType?.value as string,
      db_type: dbType,
    })
      .then((res) => {
        const treeData: TreeData[] = [];
        const { currentBizInfo } = globalBizsStore;
        if (currentBizInfo) {
          const treeId = `${ConfLevels.APP}-${currentBizInfo.bk_biz_id}`;
          const rootNode = {
            children: formatTreeData(res, treeId),
            id: currentBizInfo.bk_biz_id,
            isOpen: true,
            levelType: ConfLevels.APP,
            name: currentBizInfo.name,
            parentId: '',
            tag: confLevelInfos[ConfLevels.APP].tagText,
            treeId,
          };
          treeData.push(rootNode);
        }
        // eslint-disable-next-line no-param-reassign
        treeState.data = treeData;
        nextTick(setDefaultNode);
        // eslint-disable-next-line no-param-reassign
        treeState.isAnomalies = false;
      })
      .catch(() => {
        // eslint-disable-next-line no-param-reassign
        treeState.data = [];
        // eslint-disable-next-line no-param-reassign
        treeState.isAnomalies = true;
      })
      .finally(() => {
        // eslint-disable-next-line no-param-reassign
        treeState.loading = false;
      });
  };

  watch(
    () => clusterType,
    (val, old) => {
      if (val && val.value !== old?.value) {
        const value = val.value as ClusterTypeInfos;
        const { dbType } = clusterTypeInfos[value];
        const isBigdata = [
          ClusterTypes.DORIS,
          ClusterTypes.ES,
          ClusterTypes.HDFS,
          ClusterTypes.INFLUXDB,
          ClusterTypes.KAFKA,
          ClusterTypes.PULSAR,
          ClusterTypes.RIAK,
        ].includes(value);
        fetchBusinessTopoTree(isBigdata ? 'bigdata' : dbType);
      }
    },
    { immediate: true },
  );

  function createModule() {
    if (clusterType?.value) {
      const mysqlTypes = [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA] as string[];
      if (mysqlTypes.includes(clusterType.value)) {
        const ticketTypeMap = {
          [ClusterTypes.SQLSERVER_HA]: TicketTypes.SQLSERVER_HA_APPLY,
          [ClusterTypes.SQLSERVER_SINGLE]: TicketTypes.SQLSERVER_SINGLE_APPLY,
          [ClusterTypes.TENDBHA]: TicketTypes.MYSQL_HA_APPLY,
          [ClusterTypes.TENDBSINGLE]: TicketTypes.MYSQL_SINGLE_APPLY,
        };
        router.push({
          name: 'SelfServiceCreateDbModule',
          params: {
            bk_biz_id: globalBizsStore.currentBizId,
            type: ticketTypeMap[clusterType.value as keyof typeof ticketTypeMap],
          },
        });
      } else {
        router.push({
          name: 'createSpiderModule',
          params: {
            bizId: globalBizsStore.currentBizId,
          },
        });
      }
    }
  }

  /**
   * 格式化拓扑树节点数据
   */
  function formatTreeData(data: BizConfTopoTreeModel[], parentId: string): TreeData[] {
    if (data.length === 0) {
      return [];
    }

    return data.map((item) => {
      const treeId = `${item.obj_id}-${item.instance_id}`;
      const children = item.children ? formatTreeData(item.children, treeId) : [];
      return {
        children,
        data: item,
        id: item.instance_id,
        levelType: item.obj_id,
        name: item.obj_id === ConfLevels.CLUSTER ? item?.extra?.domain : item.instance_name,
        parentId,
        tag: confLevelInfos[item.obj_id].tagText,
        treeId,
      };
    });
  }

  return {
    createModule,
    fetchBusinessTopoTree,
    handleSelectedTreeNode,
    treePrefixIcon,
    treeRef,
    treeSearchConfig,
    treeState,
  };
};
