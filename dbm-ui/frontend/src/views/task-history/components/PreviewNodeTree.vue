<template>
  <BkPopover
    ext-cls="task-preview-node-tree-nodes"
    :is-show="isShowNodePanel"
    placement="bottom"
    theme="light"
    trigger="manual"
    :width="300"
    @after-show="handlefterShow">
    <template #content>
      <div class="tree-top-main">
        <span>
          {{ t(titleKeypath, { n: nodesCount }) }}
        </span>
        <div
          class="quick-operate"
          @click="() => (isShowNodePanel = false)">
          <div class="operate-item">
            <DbIcon type="close" />
          </div>
        </div>
      </div>
      <BkTree
        ref="treeRef"
        :children="children"
        class="tree-node-tree-main"
        :data="nodesTreeData"
        label="name"
        node-key="id"
        selectable
        :show-node-type-icon="false"
        @node-click="handleNodeClick"
        @node-expand="handleNodeClick">
        <template #node="item">
          <div class="custom-tree-node">
            <div
              class="file-icon"
              :class="[`file-icon-${theme}`]">
              <DbIcon type="file" />
            </div>
            <span
              v-overflow-tips
              class="node-name text-overflow">
              {{ item.name }}
            </span>
          </div>
        </template>
      </BkTree>
    </template>
    <span
      v-bk-tooltips="tooltips"
      class="task-preview-node-tree-num-tip"
      :class="[`task-preview-node-tree-num-tip-${theme}`, marginRight ? 'mr-8' : '']"
      @click="() => handleNodePanelSwich()">
      <I18nT
        :keypath="statusKeypath"
        tag="span">
        <span
          class="number-display"
          :class="[`number-display-${theme}`]">
          {{ nodesCount }}
        </span>
      </I18nT>
    </span>
  </BkPopover>
</template>

<script setup lang="ts">
  import { Tree } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { getTaskflowDetails } from '@services/source/taskflow';

  interface Props {
    nodesCount: number;
    nodesTreeData: ServiceReturnType<typeof getTaskflowDetails>['activities'][string][];
    statusKeypath: string;
    titleKeypath: string;
    tooltips: string;
    theme?: 'error' | 'warning';
    children?: string;
    marginRight?: boolean;
  }

  interface Emits {
    (e: 'node-click', value: Props['nodesTreeData'][number], refValue: typeof treeRef): void;
    (e: 'after-show', value: typeof treeRef): void;
  }

  interface Exposes {
    close: () => void;
    getTreeRef: () => typeof treeRef;
    isOpen: () => boolean;
  }

  withDefaults(defineProps<Props>(), {
    theme: 'error',
    children: 'children',
    marginRight: false,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowNodePanel = ref(false);
  const treeRef = ref<InstanceType<typeof Tree>>();

  const handlefterShow = () => {
    setTimeout(() => {
      emits('after-show', treeRef);
    });
  };

  const handleNodeClick = (node: Props['nodesTreeData'][number]) => {
    emits('node-click', node, treeRef);
  };

  const handleNodePanelSwich = () => {
    isShowNodePanel.value = !isShowNodePanel.value;
  };

  defineExpose<Exposes>({
    close() {
      isShowNodePanel.value = false;
    },
    getTreeRef() {
      return treeRef;
    },
    isOpen() {
      return isShowNodePanel.value === true;
    },
  });
</script>

<style lang="less">
  .task-preview-node-tree-nodes {
    z-index: 999 !important;
    max-height: 500px;
    padding: 12px 0 !important;

    .tree-top-main {
      display: flex;
      padding: 0 12px 10px;
      font-size: 12px;
      font-weight: 700;
      color: #313238;
      justify-content: space-between;
      align-items: center;

      .quick-operate {
        display: flex;

        .operate-item {
          display: flex;
          width: 20px;
          height: 20px;
          font-size: 16px;
          color: #979ba5;
          cursor: pointer;
          background: #f0f1f5;
          border-radius: 2px;
          justify-content: center;
          align-items: center;

          &:hover {
            color: #63656e;
            background: #eaebf0;
          }
        }
      }
    }

    .tree-node-tree-main {
      max-height: 450px !important;

      .bk-node-row {
        padding: 0 12px;

        &.is-selected {
          .bk-node-prefix {
            color: #3a84ff;
          }
        }
      }

      .custom-tree-node {
        display: flex;
        width: 100%;
        align-items: center;

        .file-icon {
          display: flex;
          width: 16px;
          height: 16px;
          margin-right: 8px;
          color: #ea3636;
          background: #fdd;
          border-radius: 2px;
          align-items: center;
          justify-content: center;

          .db-icon-file {
            font-size: 10px;
          }
        }

        .file-icon-error {
          color: #ea3636;
          background: #fdd;
        }

        .file-icon-warning {
          color: #ff9c01;
          background: #fff3e1;
        }
      }
    }
  }

  .task-preview-node-tree-num-tip {
    display: inline-block;
    height: 22px;
    padding: 0 8px;
    font-size: 12px;
    line-height: 22px;
    color: #ea3536;
    cursor: pointer;
    background: #fee;
    border-radius: 11px;

    .number-display {
      height: 16px;
      padding: 0 5px;
      margin-left: 5px;
      line-height: 20px;
      color: #fff;
      background: #ea3636;
      border-radius: 8px;
    }

    .number-display-error {
      color: #fdd;
      background: #ea3636;
    }

    .number-display-warning {
      color: #fff3e1;
      background: #ff9c01;
    }
  }

  .task-preview-node-tree-num-tip-error {
    color: #ea3636;
    background: #fdd;
  }

  .task-preview-node-tree-num-tip-warning {
    color: #ff9c01;
    background: #fff3e1;
  }
</style>
