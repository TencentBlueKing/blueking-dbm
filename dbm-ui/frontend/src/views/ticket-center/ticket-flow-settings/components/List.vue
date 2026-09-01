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
    <DbQuickSearch
      v-model="searchValue"
      class="mb-16"
      :data="quickSearchData"
      :placeholder="t('请输入或选择条件搜索')"
      style="width: 500px; margin-left: auto" />
    <BkAlert
      class="mb-16"
      closable>
      {{ t('父策略适用于业务下全部集群，不可删除。可按集群或集群标签增加子策略；') }}
      <strong>{{ t('优先级：子策略 > 父策略，按集群 > 按标签') }}</strong>
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
          :filter-row="null"
          :filter-value="searchValue"
          :max-height="tableMaxHeight"
          resizable
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

  const tableContentRef = ref<HTMLElement>();
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

  const { quickSearchData } = useSearchSelect();

  const {
    allTreeData,
    expandedTreeNodes,
    fetchListData,
    handleClearFilter,
    handleFilterChange,
    handlePageLimitChange,
    handlePageValueChange,
    handleSortChange,
    isLoading,
    isRequestFailed,
    isSearching,
    onExpandedTreeNodesChange,
    paginatedData,
    pagination,
    searchValue,
    tableSort,
  } = useFetchData();

  // 自定义树形展开/折叠图标：始终使用 down-shape，通过 rotate 过渡（fold: 0deg 指向下，expand: -90deg 指向右）
  // TDesign 的 treeExpandAndFoldIcon 参数类型为 TableRowData（非本项目 TableRow），需断言兼容
  const treeExpandAndFoldIcon = ((_h: any, { type }: { row: TableRow; type: 'expand' | 'fold' }) => (
    <DbIcon
      class='tree-expand-icon'
      style={{ color: '#C4C6CC', transform: type === 'fold' ? 'rotate(0deg)' : 'rotate(-90deg)' }}
      type='down-shape'
    />
  )) as any;

  // 行自定义 class（用于树形连接线 + 重复策略置灰）
  const rowClassName = ({ row }: { row: TableRow }) => {
    const classes: string[] = [];
    if (row.isChildRow) {
      classes.push(row.isLastChild ? 'is-last-child-row' : 'is-child-row');
    } else if (row.children && row.children.length > 0) {
      classes.push('is-parent-with-children');
    }
    if (row.isDuplicate) {
      classes.push('is-duplicate-row');
    }
    return classes.join(' ');
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
              <AuthTemplate
                actionId='biz_ticket_config_set'
                disabled={!row.editable}
                permission={row.permission.biz_ticket_config_set}
                resource={props.dbType}>
                {row.editable ? (
                  <BkButton
                    class='ml-16'
                    text
                    theme='primary'
                    onClick={() => handleEdit(row)}>
                    {row.ticket_type_display}
                  </BkButton>
                ) : (
                  <span class='ml-16'>{row.ticket_type_display}</span>
                )}
              </AuthTemplate>
              {row.isDuplicate && (
                <BkPopover
                  content={t('与父策略的审批设置一致，不再独立生效，可手动删除。')}
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
            <AuthTemplate
              actionId='biz_ticket_config_set'
              disabled={!row.editable}
              permission={row.permission.biz_ticket_config_set}
              resource={props.dbType}>
              {row.editable ? (
                <BkButton
                  text
                  theme='primary'
                  onClick={() => handleEdit(row)}>
                  {row.ticket_type_display}
                </BkButton>
              ) : (
                <span>{row.ticket_type_display}</span>
              )}
            </AuthTemplate>
            {row.isCustom && (
              <BkTag
                class='ml-4'
                size='small'
                theme='warning'>
                {t('自定义')}
              </BkTag>
            )}
            {!row.editable && (
              <BkPopover
                content={t('平台已锁定，不可更改设置')}
                placement='top'
                trigger='hover'>
                <BkTag
                  class='ml-4'
                  size='small'
                  theme='info'>
                  <DbIcon
                    class='mr-4'
                    type='bk-dbm-icon db-icon-lock-fill'
                  />
                  {t('平台锁定')}
                </BkTag>
              </BkPopover>
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
          // 按标签子策略：展示标签匹配文案 + 标签标识 + 已失效标记
          if (row.scopeType === 'tag') {
            return (
              <span class='scope-tag-cell'>
                <BkTag
                  class='mr-4'
                  size='small'>
                  {t('按标签')}
                </BkTag>
                <span class={{ 'is-tag-invalid': row.isTagInvalid, 'tag-display-text': true }}>{row.tagDisplay}</span>
                {row.isTagInvalid && (
                  <BkTag
                    v-bk-tooltips={t('该标签已被删除')}
                    class='ml-4'
                    size='small'
                    theme='danger'>
                    {t('已失效')}
                  </BkTag>
                )}
              </span>
            );
          }
          // 按集群子策略：展示集群列表 popover + 集群标识
          return (
            <span class='scope-cluster-cell'>
              <BkTag
                class='mr-4'
                size='small'>
                {t('按集群')}
              </BkTag>
              <ClusterPopover clusters={row.clusters} />
            </span>
          );
        }
        return <span>{t('业务下全部集群')}</span>;
      },
      title: t('生效范围'),
      width: 260,
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
            { label: t('需审批'), value: 'true' },
            { label: t('免审批'), value: 'false' },
          ],
        },
        showConfirmAndReset: true,
      },
      title: t('是否审批'),
      width: 120,
    },
    {
      cell: (_h: any, { row }: { row: TableRow }) => row.remark || '-',
      colKey: 'remark',
      title: t('备注'),
      width: 180,
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
      cell: (_h: any, { row }: { row: TableRow }) => {
        if (row.isChildRow) {
          return (
            <AuthTemplate
              actionId='biz_ticket_config_set'
              class='action-btns'
              disabled={!row.editable}
              permission={row.permission.biz_ticket_config_set}
              resource={props.dbType}>
              <BkButton
                disabled={!row.editable}
                text
                theme='primary'
                onClick={() => handleEdit(row)}>
                {t('编辑')}
              </BkButton>
              <BkButton
                disabled={!row.editable}
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
            disabled={!row.editable}
            permission={row.permission.biz_ticket_config_set}
            resource={props.dbType}>
            <BkButton
              disabled={!row.editable}
              text
              theme='primary'
              onClick={() => handleEdit(row)}>
              {t('编辑')}
            </BkButton>
            <BkButton
              disabled={!row.editable}
              text
              theme='primary'
              onClick={() => handleAddChild(row)}>
              {t('新建子策略')}
            </BkButton>
            {row.isCustom && (
              <BkButton
                disabled={!row.editable}
                text
                theme='primary'
                onClick={() => handleRestoreDefault(row)}>
                {t('恢复默认')}
              </BkButton>
            )}
          </AuthTemplate>
        );
      },
      colKey: 'row-operation',
      title: t('操作'),
      width: 160,
    },
  ]);

  const handleEdit = (data: TableRow) => {
    isEditPolicy.value = true;
    currentPolicyData.value = data.rawData;
    // 子策略编辑：找到父策略行以获取审批设置
    parentApprovalSetting.value = data.rawData.isChildPolicy
      ? allTreeData.value.find((n) => n.ticket_type === data.ticket_type && !n.isChildRow)?.configs.need_itsm
      : undefined;
    editPolicyVisible.value = true;
  };

  const handleAddChild = (data: TableRow) => {
    // 基于父策略构造子策略初始数据：继承过期配置，重置审批/范围/标识字段
    const newData = new TicketFlowDescribeModel({
      ...data.rawData,
      bk_biz_id: currentBizId,
      cluster_ids: [],
      clusters: [],
      configs: {
        ...data.rawData.configs,
        need_itsm: data.configs.need_itsm,
      },
      id: 0,
      is_child_config: true,
      parent_id: data.rawData.id,
      remark: '',
      update_at: '',
      updater: '',
    } as unknown as TicketFlowDescribeModel);
    isEditPolicy.value = false;
    currentPolicyData.value = newData;
    parentApprovalSetting.value = data.configs.need_itsm;
    editPolicyVisible.value = true;
  };

  // 删除配置并刷新列表（删除子策略 / 恢复默认共用）
  const removeConfig = async (configId: number) => {
    try {
      await deleteTicketFlowConfig({ config_ids: [configId] });
      messageSuccess(t('操作成功'));
      fetchListData();
      return true;
    } catch {
      return false;
    }
  };

  const handleRestoreDefault = (data: TableRow) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      content: () => (
        <div class='infobox-content'>
          <div class='infobox-row'>
            <span class='infobox-label'>{t('单据类型：')}</span>
            <span class='infobox-value'>{data.ticket_type_display}</span>
          </div>
          <p class='infobox-tip'>{t('恢复后该单据重新继承全局审批策略，随全局策略更新而自动同步。')}</p>
        </div>
      ),
      extCls: 'ticket-flow-settings-infobox',
      onConfirm: () => removeConfig(data.rawData.id),
      title: t('确认恢复为默认？'),
    });
  };

  const handleDeleteChild = (data: TableRow) => {
    InfoBox({
      cancelText: t('取消'),
      confirmButtonTheme: 'danger',
      confirmText: t('确认删除'),
      content: () => {
        // 按集群：域名从上往下排列（≤5 个全部展示；>5 个展示前 5 个 + "共 N 个" popover）
        const visibleClusterItems = data.clusters.slice(0, 5).map((c) => (
          <span
            key={c.cluster_id}
            class='infobox-cluster-item'>
            {c.immute_domain}
          </span>
        ));
        const clusterMore =
          data.clusters.length > 5 ? (
            <BkPopover
              v-slots={{
                content: () => (
                  <div class='infobox-cluster-overflow-list'>
                    {data.clusters.map((c) => (
                      <div
                        key={c.cluster_id}
                        class='infobox-cluster-item'>
                        {c.immute_domain}
                      </div>
                    ))}
                  </div>
                ),
              }}
              placement='top'
              theme='light'
              trigger='click'
              width={300}>
              <span class='infobox-cluster-more'>
                … {t('共')} {data.clusters.length} {t('个')}
              </span>
            </BkPopover>
          ) : null;

        const scopeContent =
          data.scopeType === 'tag' ? (
            <span class='scope-tag-cell'>
              <BkTag
                class='mr-8'
                size='small'>
                {t('按标签')}
              </BkTag>
              <span class={{ 'is-tag-invalid': data.isTagInvalid, 'tag-display-text': true }}>{data.tagDisplay}</span>
            </span>
          ) : (
            <span class='infobox-scope-text'>
              <BkTag
                class='infobox-cluster-tag'
                size='small'>
                {t('按集群')}
              </BkTag>
              <div class='infobox-cluster-list'>
                {visibleClusterItems}
                {clusterMore}
              </div>
            </span>
          );

        return (
          <div class='infobox-content'>
            <div class='infobox-row'>
              <span class='infobox-label'>{t('单据类型：')}</span>
              <span class='infobox-value'>{data.ticket_type_display}</span>
            </div>
            <div class='infobox-row infobox-row-top'>
              <span class='infobox-label'>{t('生效范围：')}</span>
              <span class='infobox-value'>{scopeContent}</span>
            </div>
            <p class='infobox-tip'>{t('删除后，所有集群将会恢复使用父策略配置，请谨慎操作！')}</p>
          </div>
        );
      },
      extCls: 'ticket-flow-settings-infobox',
      onConfirm: () => removeConfig(data.rawData.id),
      title: t('确认删除子策略？'),
    });
  };
</script>

<style lang="less">
  .ticket-flow-list-content {
    display: flex;
    height: 100%;
    padding: 16px 24px;
    overflow: hidden;
    box-sizing: border-box;
    flex-direction: column;

    .approval-text {
      color: #f59500;
    }

    .no-approval-text {
      color: #2caf5e;
    }

    // 生效范围：按标签 / 按集群 单元格
    .scope-tag-cell,
    .scope-cluster-cell {
      display: flex;
      align-items: center;
      min-width: 0;
    }

    // 标签展示文案（失效态添加删除线）
    .tag-display-text {
      font-size: 12px;
      font-weight: 400;
      line-height: 20px;

      &.is-tag-invalid {
        color: #f8b4b4;
        text-decoration-line: line-through;
      }
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
      position: relative;
      display: inline-flex;
      margin-left: -6px;
      align-items: center;

      // 树形连接线：垂直虚线（贯穿整行高度）
      .tree-line-vertical {
        position: absolute;
        top: -12px;
        bottom: 0;
        left: -5.5px;
        z-index: 0;
        width: 0;
        height: 44px;
        border-left: 1px dashed #dcdee5;
      }

      // 树形连接线：水平虚线（从垂直线连接到"子"tag）
      .tree-line-horizontal {
        position: absolute;
        top: 50%;
        left: -5.5px;
        z-index: 0;
        width: 22px;
        height: 0;
        border-top: 1px dashed #dcdee5;
      }
    }

    // 树形连接线：最后一个子策略垂直虚线 22px
    .is-last-child-row .tree-line-vertical {
      height: 22px !important;
    }

    // 首列对齐：父行无 children 时的图标占位符（与 TDesign 展开图标同宽）
    .tree-cell-parent {
      position: relative;
      display: inline-flex;
      align-items: center;

      // 父行树形连接线：垂直虚线（从展开图标下方延伸到 td 底部，与子行连接线对齐）
      .tree-line-vertical {
        position: absolute;
        top: 13px;
        bottom: 0;
        left: -22.5px;
        z-index: 0;
        width: 0;
        height: 18px;
        border-left: 1px dashed #dcdee5;
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
      padding-top: 4px;
      line-height: 22px;
      text-align: left;

      // label 居左、内容居右的左右布局
      .infobox-row {
        display: flex;
        gap: 8px;
        color: #313238;

        // 多行行：label 顶部对齐
        &.infobox-row-top {
          align-items: flex-start;
        }

        .infobox-label {
          flex-shrink: 0;
          width: 70px;
        }

        .infobox-value {
          flex: 1;
          word-break: break-all;
        }
      }

      // 弹窗内生效范围：按集群文案（从上往下）
      .infobox-scope-text {
        display: flex;
        gap: 4px;
        font-size: 12px;
        line-height: 20px;

        .infobox-cluster-tag {
          margin: 4px 4px 0 0;
        }

        .infobox-cluster-list {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .infobox-cluster-more {
          font-size: 12px;
          color: #3a84ff;
          cursor: pointer;
        }
      }

      .infobox-tip {
        padding: 12px 16px;
        margin-top: 16px;
        color: #4d4f56;
        background: var(--Neutral-9, #f5f7fa);
      }
    }
  }

  // 弹窗内集群溢出列表（popover teleport 到 body，需全局样式）
  .infobox-cluster-overflow-list {
    max-height: 200px;
    overflow-y: auto;

    .infobox-cluster-item {
      position: relative;
      padding: 2px 12px 2px 20px;
      font-size: 12px;
      line-height: 24px;

      &::before {
        position: absolute;
        top: 9px;
        left: 6px;
        width: 6px;
        height: 6px;
        background: #c4c6cc;
        border-radius: 50%;
        content: '';
      }
    }
  }
</style>
<style lang="less" scoped>
  .db-tree-table {
    display: flex;
    min-height: 0;
    flex: 1;
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
      // 子行整行相对定位（供连接线定位）
      .is-child-row .t-table__cell:first-child,
      .is-last-child .t-table__cell:first-child {
        position: relative;
      }

      // 父行有子节点时首列底部边框留空，用伪元素绘制虚线下划线（左端留空24px对齐子行padding）
      .is-parent-with-children td:first-child,
      .is-child-row td:first-child {
        position: relative;
        border-bottom: none;

        &::after {
          position: absolute;
          right: 0;
          bottom: 0;
          left: 40px; // 子行 padding-left: 24px + 1px 对齐
          height: 0;
          border-bottom: 1px solid var(--td-component-border);
          content: '';
        }
      }

      .is-parent-with-children td:first-child {
        .t-table__tree-op-icon,
        .tree-child-tag {
          margin: 0 16px 0 8px;
        }

        // 树形展开/折叠图标旋转过渡动画
        .tree-expand-icon {
          display: inline-flex;
          transition: transform 0.2s ease-in-out;
        }
      }

      // 重复策略行置灰（scoped 样式需 :deep 穿透）
      .is-duplicate-row .t-table__cell {
        color: #979ba5;
      }
    }
  }
</style>
