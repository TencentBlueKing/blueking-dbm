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
  <BkLoading :loading="isLoading">
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
            <div :class="TopoAlertContent ? 'topo-alert-box' : 'topo-box'">
              <TopoAlertContent @close="handleCloseAlert" />
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
                      {{ item.obj === 'biz' ? $t('业') : $t('集') }}
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
          <div style="height: 570px;">
            <RenderTopoHost
              :cluster-id="selectClusterId"
              :disabled-row-config="disabledRowConfig"
              :firsr-column="firsrColumn"
              :get-table-list="getTableList"
              :is-remote-pagination="isRemotePagination"
              :last-values="lastValues"
              :multiple="multiple"
              :role-filter-list="roleFilterList"
              :status-filter="statusFilter"
              :table-setting="tableSetting"
              @change="handleHostChange" />
          </div>
        </template>
      </BkResizeLayout>
    </div>
  </BkLoading>
</template>
<script setup lang="ts" generic="T extends IValue">
  import type { TableSetting } from '@components/instance-selector/Index.vue';

  import type { InstanceSelectorValues, IValue, PanelListType } from '../../Index.vue';

  import RenderTopoHost from './table/Index.vue';
  import { useTopoData } from './useTopoData';

  interface TopoTreeData {
    id: number;
    name: string;
    obj: 'biz' | 'cluster',
    count: number,
    children: Array<TopoTreeData>;
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues<T>): void
  }

  type TableConfigType = Required<PanelListType[number]>['tableConfig'];
  type TopoConfigType = Required<PanelListType[number]>['topoConfig'];

  interface Props {
    lastValues: InstanceSelectorValues<T>,
    tableSetting: TableSetting,
    multiple: NonNullable<TableConfigType['multiple']>,
    firsrColumn?: TableConfigType['firsrColumn'],
    roleFilterList?: TableConfigType['roleFilterList'],
    isRemotePagination?: TableConfigType['isRemotePagination'],
    disabledRowConfig?: TableConfigType['disabledRowConfig'],
    topoAlertContent?: TopoConfigType['topoAlertContent'],
    filterClusterId?: TopoConfigType['filterClusterId'], // 过滤的集群ID，单集群模式
    // eslint-disable-next-line vue/no-unused-properties
    getTopoList: NonNullable<TopoConfigType['getTopoList']>
    // eslint-disable-next-line vue/no-unused-properties
    getTableList: NonNullable<TableConfigType['getTableList']>,
    statusFilter?: TableConfigType['statusFilter'],
    // eslint-disable-next-line vue/no-unused-properties
    countFunc?: TopoConfigType['countFunc'],
  }

  const props = withDefaults(defineProps<Props>(), {
    firsrColumn: undefined,
    statusFilter: undefined,
    isRemotePagination: true,
    countFunc: undefined,
    disabledRowConfig: undefined,
    topoAlertContent: undefined,
    roleFilterList: undefined,
    filterClusterId: undefined,
  });
  const emits = defineEmits<Emits>();

  const treeSearch = ref('');
  const isCloseAlert = ref(false);

  const TopoAlertContent = computed(() => (!isCloseAlert.value ? props.topoAlertContent : null));
  const filterClusterId = computed(() => props.filterClusterId);

  const {
    treeRef,
    isLoading,
    treeData,
    selectClusterId,
    fetchResources,
  } = useTopoData<Record<string, any>>(filterClusterId);

  fetchResources();

  // 选中topo节点，获取topo节点下面的所有主机
  const handleNodeClick = (
    node: TopoTreeData,
    info: unknown,
    {
      __is_open: isOpen,
      __is_selected: isSelected }:
      {
        __is_open: boolean,
        __is_selected: boolean
      },
  ) => {
    const rawNode = treeRef.value.getData().data.find((item: { id: number; }) => item.id === node.id);
    selectClusterId.value = node.id;
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

  const handleHostChange = (values: InstanceSelectorValues<T>) => {
    emits('change', values);
  };

  const handleCloseAlert = () => {
    isCloseAlert.value = true;
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

      .topo-box {
        height: calc(100% - 50px);
        margin-top: 12px;
      }

      .topo-alert-box {
        height: calc(100% - 95px);
        margin-top: 12px;
      }

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
