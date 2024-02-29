<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkLoading :loading="isTreeDataLoading">
    <div class="password-instance-selector-topo">
      <BkResizeLayout
        :border="false"
        collapsible
        initial-divide="340px"
        :max="420"
        :min="320">
        <template #aside>
          <div class="topo-tree-box">
            <BkInput
              v-model="treeSearch"
              clearable
              :placeholder="t('搜索拓扑节点')" />
            <div style="height: calc(100% - 50px); margin-top: 12px">
              <BkTree
                ref="treeRef"
                children="children"
                :data="treeData"
                label="name"
                :node-content-action="['click']"
                :search="treeSearch"
                selectable
                :show-node-type-icon="false"
                virtual-render
                @node-click="handleNodeClick">
                <template #node="item">
                  <div class="custom-tree-node">
                    <span class="custom-tree-node-tag">
                      {{ item.obj === 'biz' ? '业' : '集' }}
                    </span>
                    <span
                      v-overflow-tips
                      class="custom-tree-node-name text-overflow">
                      {{ item.name }}
                    </span>
                    <span class="custom-tree-node-count">
                      {{ item.count }}
                    </span>
                  </div>
                </template>
              </BkTree>
            </div>
          </div>
        </template>
        <template #main>
          <RenderTopoHost
            :last-values="lastValues"
            :node="selectNode"
            :panel-tab-active="panelTabActive"
            :role="role"
            :table-settings="tableSettings"
            @change="handleHostChange" />
        </template>
      </BkResizeLayout>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import getSettings from '../common/tableSettings';
  import type { InstanceSelectorValues, PanelTypes } from '../common/types';

  import RenderTopoHost from './RenderTopoHost.vue';

  interface TTopoTreeData {
    id: number;
    name: string;
    obj: 'biz' | 'cluster';
    count: number;
    children: Array<TTopoTreeData>;
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  interface Props {
    lastValues: InstanceSelectorValues;
    role?: string;
    panelTabActive: PanelTypes;
  }

  const props = withDefaults(defineProps<Props>(), {
    role: '',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId, currentBizInfo } = useGlobalBizs();

  const isTreeDataLoading = ref(false);
  const treeRef = ref();
  const treeSearch = ref('');
  const selectNode = ref<TTopoTreeData>();
  const treeData = shallowRef<TTopoTreeData[]>([]);

  const tableSettings = getSettings(props.role);

  const fetchClusterTopo = () => {
    isTreeDataLoading.value = true;
    queryClusters({
      bk_biz_id: currentBizId,
      cluster_filters: [
        {
          bk_biz_id: currentBizId,
          cluster_type: props.panelTabActive,
        },
      ],
    })
      .then((data) => {
        const formatData = data.map((item) => {
          const formatDataItem = { ...item, count: item.instance_count };
          if (props.role === 'slave') {
            formatDataItem.count = item.slaves?.length || 0;
          } else if (props.role === 'proxy') {
            formatDataItem.count = item.proxies?.length || 0;
          } else if (props.role === 'master') {
            formatDataItem.count = item.masters?.length || 0;
          } else if (props.panelTabActive === 'tendbha') {
            formatDataItem.count = formatDataItem.count - (item.proxies?.length || 0);
          }
          return formatDataItem;
        });
        treeData.value = [
          {
            name: currentBizInfo?.display_name || '--',
            id: currentBizId,
            obj: 'biz',
            count: formatData.reduce((count, item) => count + item.count, 0),
            children: formatData.map((item) => ({
              id: item.id,
              name: item.cluster_name,
              obj: 'cluster',
              count: item.count,
              children: [],
            })),
          },
        ];
        setTimeout(() => {
          if (data.length > 0) {
            const [firstNode] = treeData.value;
            treeRef.value.setOpen(firstNode);
            treeRef.value.setSelect(firstNode);
            selectNode.value = firstNode;
          }
        });
      })
      .finally(() => {
        isTreeDataLoading.value = false;
      });
  };

  fetchClusterTopo();

  // 选中topo节点，获取topo节点下面的所有主机
  const handleNodeClick = (
    node: TTopoTreeData,
    { __is_open: isOpen, __is_selected: isSelected }: { __is_open: boolean; __is_selected: boolean },
  ) => {
    selectNode.value = node;

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

  const handleHostChange = (values: InstanceSelectorValues) => {
    emits('change', values);
  };
</script>

<style lang="less">
  .password-instance-selector-topo {
    display: block;
    height: 600px;
    padding-top: 16px;

    .bk-resize-layout {
      height: 100%;
    }

    .topo-tree-box {
      height: 100%;
      padding: 0 16px;

      .bk-tree {
        .bk-node-content {
          font-size: 12px;
        }

        .bk-node-prefix {
          width: 12px !important;
          height: 12px !important;
          color: #979ba5;
        }

        .bk-node-row {
          .custom-tree-node {
            display: flex;
            align-items: center;

            .custom-tree-node-tag {
              width: 20px;
              height: 20px;
              margin-right: 8px;
              line-height: 20px;
              color: white;
              text-align: center;
              background-color: #c4c6cc;
              flex-shrink: 0;
              border-radius: 50%;
            }

            .custom-tree-node-name {
              flex: 1;
            }

            .custom-tree-node-count {
              height: 16px;
              padding: 0 6px;
              line-height: 16px;
              color: #979ba5;
              background-color: #f0f1f5;
              border-radius: 2px;
              flex-shrink: 0;
            }
          }

          &.is-selected {
            color: @primary-color;
            background-color: #e1ecff;

            .custom-tree-node-tag {
              background-color: #3a84ff;
            }

            .custom-tree-node-count {
              color: white;
              background-color: #a3c5fd;
            }

            .bk-node-prefix {
              color: #3a84ff;
            }
          }
        }
      }
    }
  }
</style>
