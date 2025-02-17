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
    <div class="instance-selector-topo">
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
              :placeholder="$t('搜索拓扑节点')" />
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
                    <span class="custom-tree-node__tag">
                      {{ item.obj === 'biz' ? '业' : '集' }}
                    </span>
                    <span
                      v-overflow-tips
                      class="custom-tree-node__name text-overflow">
                      {{ item.name }}
                    </span>
                    <span class="custom-tree-node__count">
                      {{ item.count }}
                    </span>
                  </div>
                </template>
              </BkTree>
            </div>
          </div>
        </template>
        <template #main>
          <div style="height: 570px">
            <RenderContent
              :is-radio-mode="isRadioMode"
              :last-values="lastValues"
              :master-slave-map="masterSlaveMap"
              :node="selectNode"
              :role="role"
              @change="handleHostChange" />
          </div>
        </template>
      </BkResizeLayout>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { getRedisList } from '@services/source/redis';
  import { queryMasterSlavePairs } from '@services/source/redisToolbox';

  import { useGlobalBizs } from '@stores';

  import type { InstanceSelectorValues } from '../Index.vue';

  import type { PanelTypes } from './PanelTab.vue';
  import RenderRedisHost from './RenderRedisHost.vue';

  interface TopoTreeData {
    id: number;
    name: string;
    obj: 'biz' | 'cluster';
    count: number;
    children?: TopoTreeData[];
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  interface Props {
    lastValues: InstanceSelectorValues;
    role?: string;
    activeTab?: PanelTypes;
    isRadioMode?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    role: '',
    activeTab: 'idleHosts',
    isRadioMode: false,
  });
  const emits = defineEmits<Emits>();

  const { currentBizId, currentBizInfo } = useGlobalBizs();

  const isTreeDataLoading = ref(false);
  const treeRef = ref();
  const treeSearch = ref('');
  const selectNode = ref<{
    id: number;
    name: string;
  }>();
  const treeData = shallowRef<TopoTreeData[]>([]);

  const renderMap = { idleHosts: RenderRedisHost } as Record<string, any>;

  const RenderContent = computed(() => renderMap[props.activeTab as string]);

  const masterSlaveMap: Record<string, ServiceReturnType<typeof queryMasterSlavePairs>[number]> = {};

  const fetchMasterSlavePairs = (clusterIds: number[]) => {
    const taskList = clusterIds.map((id) => queryMasterSlavePairs({ cluster_id: id }));
    Promise.all(taskList).then((resultList) => {
      resultList.flat().forEach((item) => {
        masterSlaveMap[item.master_ip] = item;
      });
    });
  };

  const fetchClusterTopo = () => {
    isTreeDataLoading.value = true;
    getRedisList({
      offset: 0,
      limit: -1,
    })
      .then((data) => {
        let total = 0;
        const clusterIds: number[] = [];
        const children = data.results.reduce<TopoTreeData[]>((acc, cluster) => {
          total += cluster.count;
          clusterIds.push(cluster.id);
          return [
            ...acc,
            {
              id: cluster.id,
              name: cluster.master_domain,
              obj: 'cluster',
              count: cluster.count,
            },
          ];
        }, []);
        treeData.value = [
          {
            name: currentBizInfo?.display_name || '--',
            id: currentBizId,
            obj: 'biz',
            count: total,
            children,
          },
        ];
        fetchMasterSlavePairs(clusterIds);
        setTimeout(() => {
          if (data.results.length > 0) {
            [selectNode.value] = treeData.value;
            const [firstRawNode] = treeRef.value.getData().data;
            treeRef.value.setOpen(firstRawNode);
            treeRef.value.setSelect(firstRawNode);
          }
        });
      })
      .catch((e) => {
        console.error(e);
      })
      .finally(() => {
        isTreeDataLoading.value = false;
      });
  };

  fetchClusterTopo();

  // 选中topo节点，获取topo节点下面的所有主机
  const handleNodeClick = (
    node: TopoTreeData,
    info: unknown,
    {
      __is_open: isOpen,
      __is_selected: isSelected,
    }: {
      __is_open: boolean;
      __is_selected: boolean;
      __index: number;
    },
  ) => {
    const rawNode = treeRef.value.getData().data.find((item: { id: number }) => item.id === node.id);
    selectNode.value = node;
    if (!isOpen && !isSelected) {
      treeRef.value.setNodeOpened(rawNode, true);
      treeRef.value.setSelect(rawNode, true);
      return;
    }

    if (isOpen && !isSelected) {
      treeRef.value.setSelect(rawNode, true);
      return;
    }

    if (isSelected) {
      treeRef.value.setNodeOpened(rawNode, !isOpen);
    }
  };

  const handleHostChange = (values: InstanceSelectorValues) => {
    emits('change', values);
  };
</script>
<style lang="less">
  .instance-selector-topo {
    display: block;
    padding-top: 16px;

    .bk-resize-layout {
      height: 100%;
    }

    .topo-tree-box {
      height: 100%;
      max-height: 570px;
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

            &__tag {
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

            &__name {
              flex: 1;
            }

            &__count {
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

            .custom-tree-node__tag {
              background-color: #3a84ff;
            }

            .custom-tree-node__count {
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
