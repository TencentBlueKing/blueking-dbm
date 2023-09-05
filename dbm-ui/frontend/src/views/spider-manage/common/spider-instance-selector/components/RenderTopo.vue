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
    <div
      class="instance-selector-topo"
      :class="{'single-cluster': Boolean(clusterId)}">
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
          <div style="height: 490px;">
            <RenderTopoHost
              :cluster-id="selectClusterId"
              :last-values="lastValues"
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
  import {
    ref,
    shallowRef,
  } from 'vue';

  import { queryClusters } from '@services/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import getSettings from '../common/tableSettings';
  import type { InstanceSelectorValues } from '../Index.vue';

  import { activePanelInjectionKey } from './PanelTab.vue';
  import RenderTopoHost from './RenderTopoHost.vue';

  interface TTopoTreeData {
    id: number;
    name: string;
    obj: 'biz' | 'cluster',
    count: number,
    children: Array<TTopoTreeData>;
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void
  }

  interface Props {
    lastValues: InstanceSelectorValues,
    clusterId?: number,
    role?: string
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { currentBizId, currentBizInfo } = useGlobalBizs();
  const activePanel = inject(activePanelInjectionKey);
  const tableSettings = getSettings(props.role);

  const isTreeDataLoading = ref(false);
  const treeRef = ref();
  const treeData = shallowRef<TTopoTreeData []>([]);
  const treeSearch = ref('');
  const selectClusterId = ref<Props['clusterId']>(props.clusterId);

  const fetchClusterTopo = () => {
    if (props.clusterId) {
      selectClusterId.value = props.clusterId;
      return;
    }
    isTreeDataLoading.value = true;
    queryClusters({
      bk_biz_id: currentBizId,
      cluster_filters: [
        {
          bk_biz_id: currentBizId,
          cluster_type: activePanel?.value,
        },
      ],
    }).then((data) => {
      const formatData = data.map((item: any) => ({ ...item, count: item.instance_count }));
      treeData.value = [
        {
          name: currentBizInfo?.display_name || '--',
          id: currentBizId,
          obj: 'biz',
          count: formatData.reduce((count: number, item: any) => count + item.count, 0),
          children: formatData.map((item: any) => ({
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
          selectClusterId.value = firstNode.id;
        }
      });
    })
      .finally(() => {
        isTreeDataLoading.value = false;
      });
  };

  fetchClusterTopo();

  // 选中topo节点，获取topo节点下面的所有主机
  const handleNodeClick = (node: TTopoTreeData) => {
    selectClusterId.value = node.id;
  };

  const handleHostChange = (values: InstanceSelectorValues) => {
    emits('change', values);
  };

</script>
<style lang="less">
  .instance-selector-topo {
    display: block;
    padding-top: 16px;

    // &.single-cluster{
    //   .bk-resize-layout-aside{
    //     width: 0 !important;
    //     overflow: hidden !important;
    //   }
    // }

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
