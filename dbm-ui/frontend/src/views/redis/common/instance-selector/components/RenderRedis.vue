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
            <div style="height: calc(100% - 50px); margin-top: 12px;">
              <BkTree
                ref="treeRef"
                children="children"
                :data="treeData"
                label="cluster_name"
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
                      {{ item.master_domain }}
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
          <RenderRedisFailHost
            v-if="activeTab === 'masterFailHosts'"
            :last-values="lastValues"
            :node="selectNode"
            :role="role"
            :table-settings="tableSettings"
            @change="handleHostChange" />
          <RenderCreateSlaveRedisHost
            v-if="activeTab === 'createSlaveIdleHosts'"
            :last-values="lastValues"
            :node="selectNode"
            :role="role"
            :table-settings="tableSettings"
            @change="handleHostChange" />
          <RenderRedisHost
            v-else
            :last-values="lastValues"
            :node="selectNode"
            :role="role"
            :table-settings="tableSettings"
            @change="handleHostChange" />
        </template>
      </BkResizeLayout>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">

  import RedisModel from '@services/model/redis/redis';
  import { listClusterList } from '@services/redis/toolbox';

  import type { InstanceSelectorValues } from '../Index.vue';

  import type { PanelTypes } from './PanelTab.vue';
  import RenderCreateSlaveRedisHost from './RenderCreateSlaveRedisHost.vue';
  import RenderRedisFailHost from './RenderRedisFailHost.vue';
  import RenderRedisHost from './RenderRedisHost.vue';

  import type { TableProps } from '@/types/bkui-vue';

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void
  }

  interface Props {
    lastValues: InstanceSelectorValues,
    tableSettings: TableProps['settings'],
    role?: string,
    activeTab?: PanelTypes,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isTreeDataLoading = ref(false);
  const treeRef = ref();
  const treeData = shallowRef<RedisModel[]>([]);
  const treeSearch = ref('');
  const selectNode = ref<{
    id: number;
    name: string;
    clusterDomain: string;
  }>();

  const fetchClusterTopo = () => {
    isTreeDataLoading.value = true;
    listClusterList().then((data) => {
      console.log('listClusterList>>>', data);
      if (props.activeTab === 'masterFailHosts') {
        // 主故障切换，展示master数量
        data.forEach(item => item.count = item.redisMasterCount);
      }
      treeData.value = data;
      setTimeout(() => {
        if (data.length > 0) {
          const [firstNode] = treeData.value;
          const node = {
            id: firstNode.id,
            name: firstNode.cluster_name,
            clusterDomain: firstNode.master_domain,
          };
          treeRef.value.setOpen(firstNode);
          treeRef.value.setSelect(firstNode);
          selectNode.value = node;
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
  const handleNodeClick = async (
    node: RedisModel,
    _: any,
    { __is_open: isOpen, __is_selected: isSelected }: { __is_open: boolean, __is_selected: boolean },
  ) => {
    const item = {
      id: node.id,
      name: node.cluster_name,
      clusterDomain: node.master_domain,
    };
    selectNode.value = item;
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
  .instance-selector-topo {
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
@services/model/redis/redis
