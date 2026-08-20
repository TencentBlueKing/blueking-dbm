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
import { useRequest } from 'vue-request';

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';
import { getBigdataResourceTree } from '@services/source/bigdata';
import { getMongoDBResourceTree } from '@services/source/mongodb';
import { getMysqlResourceTree } from '@services/source/mysql';
import { getRedisResourceTree } from '@services/source/redis';
import { geSqlserverResourceTree } from '@services/source/sqlserver';

import { useGlobalBizs } from '@stores';

import { type ClusterTypeInfos, clusterTypeInfos, ClusterTypes, confLevelInfos, ConfLevels } from '@common/const';

import type { TreeData, TreeState } from '@views/db-configure/common/types';

import { getConfigureState, resetConfigureTab, saveConfigureState } from '@/views/db-configure/utils/configureState';

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
  const clusterType = inject<Ref<string>>('activeClusterType');

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

    // 保存选中的 treeNode 到 sessionStorage，同时重置 activeTab（不同节点 tabs 不同）
    saveConfigureState({
      selectedParentId: node.parentId,
      selectedTreeId: node.treeId,
    });
    resetConfigureTab();

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
        router.replace({
          params: {
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
  const findTreeNodeById = (nodes: TreeData[], targetTreeId: string): TreeData | undefined => {
    for (const node of nodes) {
      if (node.treeId === targetTreeId) {
        return node;
      }
      if (node.children?.length) {
        const found = findTreeNodeById(node.children, targetTreeId);
        if (found) return found;
      }
    }
    return undefined;
  };

  const setDefaultNode = () => {
    const { data = [] } = treeRef.value.getData();
    let node = data[0] as TreeData | undefined;
    let needSaveState = false;

    // 优先从 sessionStorage 恢复选中的 treeNode
    const savedState = getConfigureState();
    if (savedState.selectedTreeId) {
      const targetNode = findTreeNodeById(data, String(savedState.selectedTreeId));
      if (targetNode) {
        node = targetNode;
        // eslint-disable-next-line no-param-reassign
        treeState.selected = node;
        // eslint-disable-next-line no-param-reassign
        treeState.activeNode = node;
        return;
      }
    }

    const { parentId: queryParentId, treeId: queryTreeId } = route.params;
    if (queryTreeId) {
      const targetNode = findTreeNodeById(data, String(queryTreeId));
      if (targetNode) {
        node = targetNode;
        needSaveState = true; // 需要从 URL 参数保存状态
      }
    }
    // eslint-disable-next-line no-param-reassign
    treeState.selected = node;
    // eslint-disable-next-line no-param-reassign
    treeState.activeNode = node;

    // 如果从 URL 参数恢复了节点，保存到 sessionStorage
    if (needSaveState) {
      saveConfigureState({
        selectedParentId: queryParentId as string,
        selectedTreeId: queryTreeId as string,
      });
    }
  };

  /**
   * 获取拓扑树
   */
  const fetchTreeApi = (params: { bk_biz_id: number; cluster_type: string; db_type: string }) =>
    apiMap[params.db_type](params);

  const { run: runFetchTree } = useRequest(fetchTreeApi, {
    manual: true,
    onError() {
      // eslint-disable-next-line no-param-reassign
      treeState.data = [];
      // eslint-disable-next-line no-param-reassign
      treeState.isAnomalies = true;
      // eslint-disable-next-line no-param-reassign
      treeState.loading = false;
    },
    onSuccess(res) {
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
      // eslint-disable-next-line no-param-reassign
      treeState.loading = false;
    },
  });

  const fetchBusinessTopoTree = (dbType: string) => {
    // eslint-disable-next-line no-param-reassign
    treeState.loading = true;
    runFetchTree({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_type: clusterType?.value as string,
      db_type: dbType,
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

  /*
   * 创建模块
   */
  function createModule() {
    if (!clusterType?.value) return;
    router.push({
      name: 'DbConfigureCreateModule',
      params: {
        clusterType: clusterType?.value,
      },
    });
  }

  /*
   * 克隆模块
   */
  function cloneModule(query: {
    /** 源模块字符集（克隆场景，即当前模块字符集） */
    charset: string;
    /** 源模块版本（克隆场景，即当前模块版本） */
    confFile: string;
    /** 源模块 ID（克隆场景，即当前模块 ID） */
    moduleId: string | number;
    /** 源模块名称（克隆场景，即当前模块名称） */
    moduleName: string;
    /** 源模块接入层版本（克隆场景，即当前模块 spider 版本，TenDBCluster 专用） */
    spiderConfFile?: string;
  }) {
    if (!clusterType?.value) return;
    router.push({
      name: 'DbConfigureCloneModule',
      params: {
        clusterType: clusterType?.value,
      },
      query,
    });
  }

  /**
   * 格式化拓扑树节点数据
   *
   * 注意：cluster 级节点不进入树渲染（被 filter 掉），但模块（module）需要保留挂载在其下的
   * 集群信息以供"关联集群"展示，因此在构造 module 节点时把原始 cluster children
   * 单独抽取并赋值到 clusters 字段。
   */
  /**
   * 自然序排序比较函数（将字符串中的数字按数值比较）
   */
  const naturalSort = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true });

  function formatTreeData(data: BizConfTopoTreeModel[], parentId: string): TreeData[] {
    if (data.length === 0) {
      return [];
    }

    return data
      .filter((item) => item.obj_id !== ConfLevels.CLUSTER)
      .sort((a, b) => naturalSort(a.instance_name, b.instance_name))
      .map((item) => {
        const treeId = `${item.obj_id}-${item.instance_id}`;
        const isModule = item.obj_id === ConfLevels.MODULE;
        const rawChildren = item.children || [];
        const children = isModule ? [] : formatTreeData(rawChildren, treeId);
        // 模块节点：从原始 children 中抽取 cluster 子节点
        const clusters = isModule
          ? rawChildren
              .filter((child) => child.obj_id === ConfLevels.CLUSTER)
              .sort((a, b) => naturalSort(a.extra?.domain || a.instance_name, b.extra?.domain || b.instance_name))
              .map((child) => ({
                children: [],
                data: child,
                id: child.instance_id,
                levelType: child.obj_id,
                // 关联集群展示使用 extra.domain（业务可识别的访问入口），instance_name 仅作 fallback
                name: child.extra?.domain || child.instance_name,
                parentId: treeId,
                tag: confLevelInfos[child.obj_id].tagText,
                treeId: `${child.obj_id}-${child.instance_id}`,
              }))
          : undefined;
        return {
          children,
          ...(clusters ? { clusters } : {}),
          data: item,
          id: item.instance_id,
          levelType: item.obj_id,
          name: item.instance_name,
          parentId,
          tag: confLevelInfos[item.obj_id].tagText,
          treeId,
        };
      });
  }

  return {
    cloneModule,
    createModule,
    fetchBusinessTopoTree,
    handleSelectedTreeNode,
    treePrefixIcon,
    treeRef,
    treeSearchConfig,
    treeState,
  };
};
