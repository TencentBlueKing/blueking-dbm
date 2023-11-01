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
              <BkAlert
                v-if="activeTab === 'createSlaveIdleHosts'"
                closable
                style="margin-bottom: 12px;"
                theme="info"
                :title="$t('仅支持从库有故障的集群新建从库')" />
              <BkTree
                ref="treeRef"
                children="children"
                :data="treeData"
                :empty-text="$t('暂无从库故障集群')"
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
          <div style="height: 570px;">
            <RenderContent
              :is-radio-mode="isRadioMode"
              :last-values="lastValues"
              :node="selectNode"
              :role="role"
              :table-settings="tableSettings"
              @change="handleHostChange" />
          </div>
        </template>
      </BkResizeLayout>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">

  import RedisModel from '@services/model/redis/redis';
  import { listClusterList } from '@services/source/resourceRedis';

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
    isRadioMode?: boolean,
  }

  const props = withDefaults(defineProps<Props>(), {
    role: '',
    activeTab: 'idleHosts',
    isRadioMode: false,
  });
  const emits = defineEmits<Emits>();

  const isTreeDataLoading = ref(false);
  const treeRef = ref();
  const treeSearch = ref('');
  const selectNode = ref<{
    id: number;
    name: string;
    clusterDomain: string;
  }>();
  const treeData = shallowRef<RedisModel[]>([]);

  const renderMap = {
    masterFailHosts: RenderRedisFailHost,
    createSlaveIdleHosts: RenderCreateSlaveRedisHost,
    idleHosts: RenderRedisHost,
  } as Record<string, any>;

  const RenderContent = computed(() => renderMap[props.activeTab as string]);

  const fetchClusterTopo = () => {
    isTreeDataLoading.value = true;
    listClusterList().then((data) => {
      let arr = data;
      if (props.activeTab === 'masterFailHosts') {
        // 主故障切换，展示master数量
        arr.forEach((item) => {
          Object.assign(item, {
            count: item.redisMasterCount,
          });
        });
      }
      if (props.activeTab === 'createSlaveIdleHosts') {
        // 只展示master数量
        arr.forEach((item) => {
          Object.assign(item, {
            count: item.redisSlaveFaults,
          });
        });
        arr = arr.filter(item => item.redis_slave.filter(slave => slave.status !== 'running').length > 0);
      }
      treeData.value = arr;
      setTimeout(() => {
        if (arr.length > 0) {
          const [firstNode] = treeData.value;
          const [firstRawNode] = treeRef.value.getData().data;
          const node = {
            id: firstNode.id,
            name: firstNode.cluster_name,
            clusterDomain: firstNode.master_domain,
          };
          treeRef.value.setOpen(firstRawNode);
          treeRef.value.setSelect(firstRawNode);
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
  const handleNodeClick = (
    node: RedisModel,
    info: unknown,
    {
      __is_open: isOpen,
      __is_selected: isSelected,
      __index: index }: {
        __is_open: boolean,
        __is_selected: boolean,
        __index: number },
  ) => {
    const rawNode = treeRef.value.getData().data[index];
    const item = {
      id: node.id,
      name: node.cluster_name,
      clusterDomain: node.master_domain,
    };
    selectNode.value = item;
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
