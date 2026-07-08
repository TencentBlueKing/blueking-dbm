<!--
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
-->

<template>
  <div class="ticket-flow-list-content">
    <div class="top-operation">
      <div class="filter-tabs">
        <div
          class="filter-tab"
          :class="{ active: activeTab === 'all' }"
          @click="handleTabChange('all')">
          {{ t('全部') }}
          <span class="tab-count">{{ allCount }}</span>
        </div>
        <div
          class="filter-tab"
          :class="{ active: activeTab === 'noApproval' }"
          @click="handleTabChange('noApproval')">
          {{ t('免审批') }}
          <span class="tab-count">{{ noApprovalCount }}</span>
        </div>
      </div>
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto" />
    </div>
    <BkAlert
      class="mb-16"
      closable>
      {{ t('业务策略适用于业务下全部集群，不可删除。如需对指定集群单独设置，可添加子策略覆盖。') }}
    </BkAlert>
    <div
      ref="tableContentRef"
      class="db-tree-table">
      <BkLoading
        :loading="isLoading"
        :z-index="2">
        <EnhancedTable
          ref="tableRef"
          v-model:expanded-tree-nodes="expandedTreeNodes"
          :columns="columns"
          :data="paginatedData"
          :filter-value="searchValue"
          :max-height="tableMaxHeight"
          :row-class-name="rowClassName"
          row-key="id"
          :sort="tableSort"
          :tree="{
            childrenKey: 'children',
            defaultExpandAll: true,
            expandTreeNodeOnClick: false,
            indent: 24,
            treeNodeColumnIndex: 0,
          }"
          :tree-expand-and-fold-icon="treeExpandAndFoldIcon"
          @expanded-tree-nodes-change="onExpandedTreeNodesChange"
          @filter-change="handleFilterChange"
          @sort-change="handleSortChange">
          <template #empty>
            <EmptyStatus
              :is-anomalies="isRequestFailed"
              :is-searching="isSearching"
              @clear-search="handleClearFilter"
              @refresh="fetchListData" />
          </template>
        </EnhancedTable>
        <div class="table-footer">
          <BkPagination
            v-bind="pagination"
            :layout="['total', 'limit', 'list']"
            @change="handlePageValueChange"
            @limit-change="handlePageLimitChange" />
        </div>
      </BkLoading>
    </div>
  </div>
  <EditPolicySide
    v-model:is-show="editPolicyVisible"
    :data="currentPolicyData"
    :is-edit="isEditPolicy"
    :parent-approval-setting="parentApprovalSetting"
    @success="fetchListData" />
</template>

<script setup lang="tsx">
  import { Alert as BkAlert, Button as BkButton, InfoBox, Popover as BkPopover, Tag as BkTag } from 'bkui-vue';
  import { EnhancedTable } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { deleteTicketFlowConfig } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import type { DBTypes } from '@common/const';

  import AuthTemplate from '@components/auth-component/component.vue';
  import DbIcon from '@components/db-icon/index';
  import DbQuickSearch from '@components/db-quick-search/Index.vue';
  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { messageSuccess } from '@utils';

  import { type TableRow, useFetchData } from '../hooks/use-fetch-data';
  import { useSearchSelect } from '../hooks/use-search-select';

  import ClusterPopover from './ClusterPopover.vue';
  import EditPolicySide from './EditPolicySide.vue';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  // 表格容器引用（用于动态计算表格可用高度）
  const tableContentRef = ref<HTMLElement>();
  // 表格最大高度（由 ResizeObserver 根据容器高度实时计算）
  const tableMaxHeight = ref(600);
  let resizeObserver: ResizeObserver | null = null;

  const updateTableMaxHeight = () => {
    if (tableContentRef.value) {
      // 减去底部分页 footer 高度（约 60px）
      tableMaxHeight.value = tableContentRef.value.clientHeight - 60;
    }
  };

  onMounted(() => {
    if (tableContentRef.value) {
      resizeObserver = new ResizeObserver(updateTableMaxHeight);
      resizeObserver.observe(tableContentRef.value);
      updateTableMaxHeight();
    }
  });

  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
  });

  const editPolicyVisible = ref(false);
  const isEditPolicy = ref(false);
  const currentPolicyData = ref<TicketFlowDescribeModel>(new TicketFlowDescribeModel());
  const parentApprovalSetting = ref<boolean | undefined>(undefined);

  // 搜索选择器配置（搜索值的读写与 URL 同步统一由 useFetchData 通过 useUrlSearch 管理）
  const { quickSearchData } = useSearchSelect();

  // 数据获取 hook：内部统一持有 activeTab / pagination / searchValue 并通过 URL 同步
  const {
    activeTab,
    allCount,
    allTreeData,
    expandedTreeNodes,
    fetchListData,
    handleClearFilter,
    handleFilterChange,
    handlePageLimitChange,
    handlePageValueChange,
    handleSortChange,
    handleTabChange,
    isLoading,
    isRequestFailed,
    isSearching,
    noApprovalCount,
    onExpandedTreeNodesChange,
    paginatedData,
    pagination,
    searchValue,
    tableSort,
  } = useFetchData();

  // 自定义树形展开/折叠图标 (TDesign: (h, { type, row }) => VNode)
  const treeExpandAndFoldIcon = ((h: any, { type }: { row: TableRow; type: 'expand' | 'fold' }) => {
    return h(DbIcon, { style: { color: '#C4C6CC' }, type: type === 'expand' ? 'right-shape' : 'down-shape' });
  }) as any;

  // 行自定义 class（用于树形连接线 + 重复策略置灰）
  const rowClassName = ({ row }: { row: TableRow }) => {
    if (row.isDuplicate) return 'is-duplicate-row';
    if (row.isChildRow) return 'is-child-row';
    if (row.children && row.children.length > 0) return 'is-parent-with-children';
    return '';
  };

  /**
   * 列定义
   */
  const columns = computed((): any => [
    {
      cell: (_h: any, { row }: { row: TableRow }) => {
        if (row.isChildRow) {
          // 子行：用负 margin 抵消 TDesign 树形 indent(24px)，使"子"tag 与展开图标对齐
          // 同时渲染树形连接线（垂直虚线 + 水平虚线）
          return (
            <span class='tree-cell-child'>
              {/* 树形连接线：垂直虚线 */}
              <span class='tree-line-vertical' />
              {/* 树形连接线：水平虚线 */}
              <span class='tree-line-horizontal' />
              <BkTag
                class='tree-child-tag'
                size='small'
                theme='warning'>
                {t('子')}
              </BkTag>
              <span class='ml-16'>{row.ticket_type_display}</span>
              {row.isDuplicate && (
                <BkPopover
                  content={t('与「业务下全部集群」的审批设置一致，不再独立生效。可手动删除。')}
                  placement='top'
                  trigger='hover'>
                  <BkTag
                    class='ml-4'
                    size='small'>
                    {t('重复')}
                  </BkTag>
                </BkPopover>
              )}
            </span>
          );
        }
        // 父行：无 children 时添加占位元素（与 TDesign 展开图标同宽），使文本对齐
        const hasChildren = row.children && row.children.length > 0;
        return (
          <span class='tree-cell-parent'>
            {/* 树形连接线：垂直虚线 */}
            {hasChildren && expandedTreeNodes.value.includes(row.id) && <span class='tree-line-vertical' />}
            {!hasChildren && <span class='tree-icon-placeholder' />}
            <span>{row.ticket_type_display}</span>
            {row.isCustom && (
              <BkTag
                class='ml-4'
                size='small'
                theme='warning'>
                {t('自定义')}
              </BkTag>
            )}
          </span>
        );
      },
      colKey: 'ticket_type',
      render: () => <span class='ml-38'>{t('单据类型')}</span>,
      width: 260,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => {
        if (row.isChildRow) {
          return <ClusterPopover clusters={row.clusters} />;
        }
        return <span>{t('业务下全部集群')}</span>;
      },
      title: t('生效范围'),
      width: 200,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => {
        if (row.configs.need_itsm) {
          return <span class='approval-text'>{t('需审批')}</span>;
        }
        return <span class='no-approval-text'>{t('免审批')}</span>;
      },
      colKey: 'need_itsm',
      filter: {
        component: markRaw(MultipleSelect),
        name: t('是否审批'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        props: {
          list: [
            { label: t('需审批'), value: true },
            { label: t('免审批'), value: false },
          ],
        },
        showConfirmAndReset: true,
      },
      title: t('是否审批'),
      width: 120,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => row.updater,
      colKey: 'updater',
      title: t('更新人'),
      width: 100,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => row.updateAtDisplay,
      colKey: 'updateAtDisplay',
      sorter: true,
      title: t('更新时间'),
      width: 180,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => row.remark || '-',
      colKey: 'remark',
      title: t('备注'),
      width: 180,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => {
        if (row.isChildRow) {
          return (
            <AuthTemplate
              actionId='biz_ticket_config_set'
              class='action-btns'
              permission={row.permission.biz_ticket_config_set}
              resource={props.dbType}>
              <BkButton
                text
                theme='primary'
                onClick={() => handleEdit(row)}>
                {t('编辑')}
              </BkButton>
              <BkButton
                text
                theme='primary'
                onClick={() => handleDeleteChild(row)}>
                {t('删除')}
              </BkButton>
            </AuthTemplate>
          );
        }
        return (
          <AuthTemplate
            actionId='biz_ticket_config_set'
            class='action-btns'
            permission={row.permission.biz_ticket_config_set}
            resource={props.dbType}>
            <BkButton
              text
              theme='primary'
              onClick={() => handleEdit(row)}>
              {t('编辑')}
            </BkButton>
            {row.children && row.children.length > 0 ? (
              <BkPopover
                content={t('已存在子策略，不可重复创建')}
                placement='top'
                trigger='hover'>
                <BkButton
                  disabled
                  text
                  theme='primary'>
                  {t('新建子策略')}
                </BkButton>
              </BkPopover>
            ) : (
              <BkButton
                text
                theme='primary'
                onClick={() => handleAddChild(row)}>
                {t('新建子策略')}
              </BkButton>
            )}
            {row.isCustom && (
              <BkButton
                text
                theme='primary'
                onClick={() => handleRestoreDefault(row)}>
                {t('恢复默认')}
              </BkButton>
            )}
          </AuthTemplate>
        );
      },
      colKey: 'action',
      title: t('操作'),
      width: 200,
    },
  ]);

  const handleEdit = (data: TableRow) => {
    isEditPolicy.value = true;
    currentPolicyData.value = data.rawData;
    if (data.rawData.isChildPolicy) {
      // 找到父策略行以获取审批设置
      const findParent = (nodes: TableRow[]): TableRow | undefined => {
        for (const node of nodes) {
          if (node.ticket_type === data.ticket_type && !node.isChildRow) {
            return node;
          }
        }
        return undefined;
      };
      const parentRow = findParent(allTreeData.value);
      parentApprovalSetting.value = parentRow ? parentRow.configs.need_itsm : undefined;
    } else {
      parentApprovalSetting.value = undefined;
    }
    editPolicyVisible.value = true;
  };

  const handleAddChild = (data: TableRow) => {
    const newData = new TicketFlowDescribeModel(
      Object.assign({}, data.rawData, {
        bk_biz_id: currentBizId,
        cluster_ids: [],
        clusters: [],
        configs: {
          expire_config: {
            flow_todo_expire: -1,
            inner_flow_expire: -1,
            itsm_expire: -1,
          },
          need_itsm: data.configs.need_itsm,
        },
        id: 0,
        is_child_config: true,
        parent_id: data.rawData.id,
        remark: '',
        update_at: '',
        updater: '',
      }),
    );
    isEditPolicy.value = false;
    currentPolicyData.value = newData;
    parentApprovalSetting.value = data.configs.need_itsm;
    editPolicyVisible.value = true;
  };

  const handleDeleteChild = (data: TableRow) => {
    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      confirmText: t('确认删除'),
      content: () => (
        <div class='infobox-content'>
          <p>
            {t('单据类型')}：{data.ticket_type_display}
          </p>
          <p class='infobox-tip'>{t('删除后，所有集群将会恢复使用父策略配置，请谨慎操作！')}</p>
        </div>
      ),
      extCls: 'ticket-flow-settings-infobox',
      onConfirm: async () => {
        try {
          await deleteTicketFlowConfig({
            config_ids: [data.rawData.id],
          });
          messageSuccess(t('操作成功'));
          fetchListData();
          return true;
        } catch {
          return false;
        }
      },
      title: t('确认删除子策略？'),
    });
  };

  const handleRestoreDefault = (data: TableRow) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      content: () => (
        <div class='infobox-content'>
          <p>
            {t('单据类型')}：{data.ticket_type_display}
          </p>
          <p class='infobox-tip'>{t('恢复后该单据重新继承全局审批策略，随全局策略更新而自动同步。')}</p>
        </div>
      ),
      extCls: 'ticket-flow-settings-infobox',
      onConfirm: async () => {
        try {
          await deleteTicketFlowConfig({
            config_ids: [data.rawData.id],
          });
          messageSuccess(t('操作成功'));
          fetchListData();
          return true;
        } catch {
          return false;
        }
      },
      title: t('确认恢复为默认？'),
    });
  };
</script>

<style lang="less">
  .ticket-flow-list-content {
    display: flex;
    height: 100%;
    padding: 16px 24px;
    box-sizing: border-box;
    flex-direction: column;
    overflow: hidden;

    .top-operation {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      .filter-tabs {
        display: flex;
        height: 32px;
        padding: 4px;
        align-items: center;
        border-radius: 2px;
        background: var(--Neutral-7, #eaebf0);

        .filter-tab {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 4px;
          height: 24px;
          padding: 5px 12px;
          border-radius: 2px;
          color: #63656e;
          cursor: pointer;

          &.active {
            color: #3a84ff;
            border-radius: 2px;
            background: var(--Neutral-11, #fff);
            box-shadow: 0 2px 4px 0 #0000001a;
          }

          .tab-count {
            display: flex;
            height: 16px;
            padding: 0 6px;
            align-items: center;
            align-content: center;
            gap: 0 6px;
            flex-wrap: wrap;
            border-radius: 8px;
            font-size: 12px;
          }
        }

        .filter-tab.active .tab-count {
          background: var(--Brand-6, #e1ecff);
        }

        .filter-tab:not(.active) .tab-count {
          background: var(--Neutral-11, #fff);
        }
      }
    }

    .approval-text {
      color: #f59500;
    }

    .no-approval-text {
      color: #2caf5e;
    }

    .action-btns {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    // 重复策略行置灰
    .is-duplicate-row {
      color: #979ba5;

      .t-table__cell {
        color: #979ba5;
      }

      .approval-text {
        color: #f9c87d;
      }

      .no-approval-text {
        color: #a1e3ba;
      }
    }

    .tree-child-tag {
      position: absolute;
      left: -14px;
      z-index: 1;
    }

    // 首列对齐：子行抵消 TDesign 树形 indent，使"子"tag 与展开图标对齐
    .tree-cell-child {
      display: inline-flex;
      align-items: center;
      margin-left: -6px;
      position: relative;

      // 树形连接线：垂直虚线（贯穿整行高度）
      .tree-line-vertical {
        position: absolute;
        left: -5.5px;
        top: -12px;
        bottom: 0;
        width: 0;
        height: 22px;
        border-left: 1px dashed #dcdee5;
        z-index: 0;
      }

      // 树形连接线：水平虚线（从垂直线连接到"子"tag）
      .tree-line-horizontal {
        position: absolute;
        left: -5.5px;
        top: 50%;
        width: 22px;
        height: 0;
        border-top: 1px dashed #dcdee5;
        z-index: 0;
      }
    }

    // 首列对齐：父行无 children 时的图标占位符（与 TDesign 展开图标同宽）
    .tree-cell-parent {
      display: inline-flex;
      align-items: center;
      position: relative;

      // 父行树形连接线：垂直虚线（从展开图标下方延伸到 td 底部，与子行连接线对齐）
      .tree-line-vertical {
        position: absolute;
        left: -22.5px;
        top: 13px;
        bottom: 0;
        width: 0;
        height: 18px;
        border-left: 1px dashed #dcdee5;
        z-index: 0;
      }

      .tree-icon-placeholder {
        display: inline-block;
        width: 32px;
        flex-shrink: 0;
      }
    }
  }

  // InfoBox
  .ticket-flow-settings-infobox {
    .infobox-content {
      text-align: left;

      .infobox-tip {
        display: flex;
        padding: 12px 16px;
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
        align-self: stretch;
        background: var(--Neutral-9, #f5f7fa);
        margin-top: 16px;
      }
    }
  }
</style>
<style lang="less" scoped>
  .db-tree-table {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;

    .table-footer {
      position: relative;
      z-index: 1;
      display: flex;
      height: 60px;
      padding: 0 16px;
      margin-top: -1px;
      background: #fff;
      border-top: 1px solid var(--td-component-border);
      align-items: center;

      :deep(.bk-pagination) {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }

    // 树形连接线：使用 :deep() 穿透 scoped 样式
    :deep(.t-table__body) {
      // 父行有子节点时首列底部边框留空，用伪元素绘制虚线下划线（左端留空24px对齐子行padding）
      .is-parent-with-children td:first-child {
        position: relative;
        border-bottom: none;

        &::after {
          content: '';
          position: absolute;
          left: 40px; // 子行 padding-left: 24px + 1px 对齐
          right: 0;
          bottom: 0;
          height: 0;
          border-bottom: 1px solid var(--td-component-border);
        }

        .t-table__tree-op-icon,
        .tree-child-tag {
          margin: 0 16px 0 8px;
        }
      }

      // 子行整行相对定位（供连接线定位）
      .is-child-row .t-table__cell:first-child {
        position: relative;
      }

      // 重复策略行置灰（scoped 样式需 :deep 穿透）
      .is-duplicate-row .t-table__cell {
        color: #979ba5;
      }
    }
  }
</style>
