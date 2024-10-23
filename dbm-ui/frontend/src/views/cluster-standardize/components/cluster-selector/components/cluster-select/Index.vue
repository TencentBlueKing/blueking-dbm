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
    <div class="selector-topo">
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
            <div class="topo-alert-box">
              <BkTree
                ref="treeRef"
                children="children"
                :data="treeData"
                label="name"
                :node-content-action="['click']"
                node-key="id"
                :search="treeSearch"
                selectable
                :selected="selectedTreeNode"
                :show-node-type-icon="false"
                virtual-render
                @node-click="handleNodeClick">
                <template #node="item">
                  <div
                    class="custom-tree-node"
                    :class="{
                      'is-leaf': !item.children,
                    }">
                    <span
                      v-if="item.nodeType"
                      class="custom-tree-node-tag">
                      {{ item.nodeType === 'biz' ? t('业') : t('模') }}
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
          <div style="height: 570px">
            <Table
              :active-panel-id="activePanelId"
              :last-values="lastValues"
              :selected-tree-node="selectedTreeNode"
              @change="handleHostChange" />
          </div>
        </template>
      </BkResizeLayout>
    </div>
  </BkLoading>
</template>
<script setup lang="ts" generic="T extends ServiceReturnType<typeof queryAllTypeCluster>['results'][number]">
  import { useI18n } from 'vue-i18n';

  import type { queryAllTypeCluster } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';

  import { useTopoData } from './hooks/useTopoData';
  import Table from './Table.vue';

  interface Props {
    lastValues: Record<string, T[]>;
    activePanelId?: string;
  }

  interface Emits {
    (e: 'change', value: Props['lastValues']): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    activePanelId: ClusterTypes.TENDBHA,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const treeSearch = ref('');

  const { treeRef, isLoading, treeData, selectedTreeNode, fetchResources, handleNodeClick } = useTopoData(
    props.activePanelId,
  );

  fetchResources();

  const handleHostChange = (values: Props['lastValues']) => {
    emits('change', values);
  };
</script>
<style lang="less">
  .selector-topo {
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

          .is-leaf {
            padding-left: 10px;
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
