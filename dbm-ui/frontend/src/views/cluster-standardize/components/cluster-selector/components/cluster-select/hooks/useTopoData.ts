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
import type BizModuleTopoTree from '@services/model/config/biz-module-topo-tree';
import { getBizModuleTopoTree } from '@services/source/cmdb';

import { ClusterTypes } from '@common/const';

/**
 * 处理集群列表数据
 */
export function useTopoData() {
  const isLoading = ref(false);
  const treeRef = ref();
  const treeData = shallowRef<BizModuleTopoTree[]>([]);
  const selectedTreeNode = shallowRef<BizModuleTopoTree>();

  /**
   * 获取列表
   */
  const fetchResources = async () => {
    isLoading.value = true;
    const params = {
      bk_biz_id: 3, // TODO 联调时要调整
      cluster_type: ClusterTypes.TENDBHA,
    };
    return getBizModuleTopoTree(params)
      .then((data) => {
        treeData.value = data;
        setTimeout(() => {
          if (data.length > 0) {
            const [firstNode] = treeData.value;
            selectedTreeNode.value = firstNode;
          }
        });
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  // 选中topo节点，获取topo节点下面的所有集群
  const handleNodeClick = (
    node: BizModuleTopoTree,
    info: unknown,
    {
      __is_open: isOpen,
      __is_selected: isSelected,
    }: {
      __is_open: boolean;
      __is_selected: boolean;
    },
  ) => {
    selectedTreeNode.value = node;
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

  return {
    treeRef,
    isLoading,
    treeData,
    selectedTreeNode,
    fetchResources,
    handleNodeClick,
  };
}
