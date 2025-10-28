<template>
  <div class="my-alarm-subscription-page">
    <div class="top-operation-main">
      <div class="batch-operations">
        <BkButton
          v-bk-tooltips="{
            content: t('请先勾选集群'),
            disabled: !!selectedList.length,
          }"
          :disabled="!selectedList.length"
          @click="() => (isShowEditSubscription = true)">
          {{ t('批量设置订阅') }}
        </BkButton>
        <BkButton
          v-bk-tooltips="{
            content: t('请先勾选集群'),
            disabled: !!selectedList.length,
          }"
          :disabled="!selectedList.length"
          @click="() => (isShowDeleteSubscription = true)">
          {{ t('批量删除订阅') }}
        </BkButton>
      </div>
    </div>
    <div class="table-main">
      <div ref="tableWrapper">
        <PrimaryTable
          ref="table"
          class="alarm-subscription-table"
          :data="tableData"
          :ellipsis="false"
          :max-height="tableMaxHeight"
          resizable
          row-class-name="alarm-subscription-table-row"
          row-key="id"
          title-ellipsis
          @change="handleFilterChange">
          <TableColumn
            col-key="id"
            fixed="left"
            resizable
            :width="60">
            <template #title>
              <div class="table-selection-head">
                <div
                  v-if="isWholeChecked"
                  class="db-table-whole-check"
                  @click="() => handleToggleWholeSelect(false)" />
                <template v-else>
                  <BkCheckbox
                    v-if="isCurrentPageAllSelected"
                    key="page"
                    label
                    model-value
                    @change="handleTogglePageSelect" />
                  <BkCheckbox
                    v-else
                    key="all"
                    @change="handleToggleWholeSelect" />
                </template>
                <BkPopover
                  :arrow="false"
                  placement="bottom-start"
                  theme="light ticket-table-select-menu"
                  trigger="hover">
                  <DbIcon
                    class="select-menu-flag"
                    type="down-big" />
                  <template #content>
                    <div class="select-menu">
                      <div
                        class="select-menu-item"
                        :class="{ 'is-selected': isCurrentPageAllSelected }"
                        @click="() => handleTogglePageSelect(true)">
                        {{ t('本页全选') }}
                      </div>
                      <div
                        class="select-menu-item"
                        :class="{ 'is-selected': isWholeChecked }"
                        @click="() => handleToggleWholeSelect(true)">
                        {{ t('跨页全选') }}
                      </div>
                    </div>
                  </template>
                </BkPopover>
              </div>
            </template>
            <template #default="{ row }: { row: IRowData }">
              <BkCheckbox
                label
                :model-value="Boolean(rowSelectMemo[row.id])"
                @change="handleSelectionChange(row)" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="id"
            resizable
            title="ID"
            :width="100">
            <template #default="{ row }: { row: IRowData }">
              <BkButton
                text
                theme="primary"
                @click="() => handleEditSubscription(row)">
                {{ row.id }}
              </BkButton>
            </template>
          </TableColumn>
          <TableColumn
            col-key="master_domain"
            resizable
            :title="t('域名')"
            :width="420">
            <template #default="{ row }: { row: IRowData }">
              <BkButton
                text
                theme="primary"
                @click="() => handleGoClusterDetailPage(row)">
                {{ row.master_domain }}
              </BkButton>
            </template>
          </TableColumn>
          <TableColumn
            col-key="db_type"
            :filter="tableFilter['db_type']"
            resizable
            :title="t('DB 类型')"
            :width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ dbTypeNameMap[row.db_type] }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="bk_biz_id"
            :filter="tableFilter['biz_id']"
            resizable
            :title="t('业务')"
            :width="150">
            <template #default="{ row }: { row: IRowData }">
              {{ bizIdMap.get(row.bk_biz_id)?.name || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="conditions"
            resizable
            :title="t('指标')"
            :width="80">
            <template #default="{ row }: { row: IRowData }">
              <BkButton
                text
                theme="primary"
                @click="() => handleEditSubscription(row)">
                {{ metricsMap[row.cluster_type].list.length }}
              </BkButton>
            </template>
          </TableColumn>
          <TableColumn
            col-key="alert_severity"
            resizable
            :title="t('告警级别')"
            :width="320">
            <template #default="{ row }: { row: IRowData }">
              <AlertSeverityGroup
                v-model="row.alert_severity"
                v-bk-loading="{ isLoading: saveLoading }"
                class="alarm-level-column"
                @change="(data) => handleAlarmLevelChange(row, data)" />
            </template>
          </TableColumn>
          <TableColumn
            col-key="notice_ways"
            resizable
            :title="t('通知渠道')"
            :width="320">
            <template #default="{ row }: { row: IRowData }">
              <NoticeWaysGroup
                v-model="row.notice_ways"
                v-bk-loading="{ isLoading: saveLoading }"
                class="notify-channel-column"
                @change="(data) => handleNotifyChannelChange(row, data)" />
            </template>
          </TableColumn>
          <TableColumn
            fixed="right"
            resizable
            :title="t('操作')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              <BkButton
                text
                theme="primary"
                @click="() => handleEditSubscription(row)">
                {{ t('编辑') }}
              </BkButton>
              <BkPopConfirm
                :content="t('删除操作无法撤回，请谨慎操作！')"
                ext-cls="delete-subscription-pop-confirm"
                placement="bottom"
                :title="t('确认删除该告警订阅？')"
                trigger="click"
                :width="280"
                @confirm="() => handleConfirmDelete(row.id)">
                <BkButton
                  class="ml-12"
                  :loading="deleteLoading"
                  text
                  theme="primary">
                  {{ t('删除') }}
                </BkButton>
              </BkPopConfirm>
            </template>
          </TableColumn>
          <template #empty>
            <EmptyStatus
              :is-anomalies="false"
              :is-searching="false" />
          </template>
        </PrimaryTable>
        <div class="table-footer">
          <BkPagination
            v-bind="pagination"
            :layout="['total', 'limit', 'list']"
            @change="handlePageValueChange"
            @limit-change="handlePageLimitChange">
            <template
              v-if="selectedList.length > 0"
              #limitAppend>
              <I18nT
                class="ml-8"
                keypath="已选择n条"
                scope="global"
                tag="span">
                <span class="number">{{ selectedList.length }}</span>
              </I18nT>
            </template>
          </BkPagination>
        </div>
      </div>
    </div>
  </div>
  <BatchEditSubscription
    v-model:is-show="isShowEditSubscription"
    :selected="selectedList"
    :show-update="false" />
  <BatchDeleteSubscription
    v-model:is-show="isShowDeleteSubscription"
    :selected="selectedList"
    :show-update="false"
    @success="() => (rowSelectMemo = {})" />
  <EditSingleSubscription
    v-model:is-show="isShowEditSingleSubscription"
    :data="currentRowData" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import type { TableChangeData, TableColumnFilter } from '@blueking/tdesign-ui';

  import { deleteSubscribe, saveSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe, useGlobalBizs } from '@stores';

  import { clusterTypeListPageMap, DBTypeInfos } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import BatchDeleteSubscription from '@views/db-manage/common/cluster-batch-delete-subscription/Index.vue';
  import AlertSeverityGroup from '@views/db-manage/common/cluster-batch-edit-subscription/components/content/components/AlertSeverityGroup.vue';
  import NoticeWaysGroup from '@views/db-manage/common/cluster-batch-edit-subscription/components/content/components/NoticeWaysGroup.vue';
  import BatchEditSubscription from '@views/db-manage/common/cluster-batch-edit-subscription/Index.vue';

  import { getOffset, messageSuccess } from '@utils';

  import EditSingleSubscription from './components/EditSingleSubscription.vue';

  export type IRowData = (typeof subscribedDomainInfo.dataList)[number];

  const { t } = useI18n();
  const router = useRouter();
  const { bizIdMap, bizs } = useGlobalBizs();
  const rootRef = useTemplateRef('tableWrapper');
  const { initSubscribedDomainInfo, metricsMap, subscribedDomainInfo } = useAlarmSubscribe();

  const tableMaxHeight = ref<number | 'auto'>('auto');
  const rowSelectMemo = ref<Record<number, IRowData>>({});
  const isCurrentPageAllSelected = ref(false);
  const isWholeChecked = ref(false);
  const isShowEditSubscription = ref(false);
  const isShowDeleteSubscription = ref(false);
  const isShowEditSingleSubscription = ref(false);
  const currentRowData = ref<IRowData>();
  const tableData = ref<IRowData[]>([]);

  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 20,
    limitList: [10, 20, 50, 100, 200, 500],
  });

  const selectedList = computed(() =>
    Object.values(rowSelectMemo.value).map((item) =>
      Object.assign(item, {
        cluster_name: item.master_domain,
      }),
    ),
  );

  const tableFilter = computed<Record<string, TableColumnFilter>>(() => {
    const panelStyle = {
      maxHeight: '280px',
      overflowY: 'auto',
      padding: '10px',
      position: 'relative',
      width: '200px',
    };
    return {
      biz_id: {
        list: bizs.map((item) => ({
          label: item.name,
          value: item.bk_biz_id,
        })),
        showConfirmAndReset: true,
        style: panelStyle,
        type: 'single',
      },
      db_type: {
        list: Object.values(DBTypeInfos).map((item) => ({
          label: item.name,
          value: item.id,
        })),
        showConfirmAndReset: true,
        style: panelStyle,
        type: 'single',
      },
    };
  });

  let filteredTableData: IRowData[] = [];

  const dbTypeNameMap = Object.values(DBTypeInfos).reduce<Record<string, string>>(
    (dataMap, item) => Object.assign(dataMap, { [item.id]: item.name }),
    {},
  );

  const { loading: saveLoading, run: runSaveSubscribe } = useRequest(saveSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('保存成功');
    },
  });

  const { loading: deleteLoading, run: runDeleteSubscribe } = useRequest(deleteSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('删除成功');
      initSubscribedDomainInfo();
    },
  });

  const refreshTableData = (isFilter = false) => {
    const start = (pagination.current - 1) * pagination.limit;
    const end = start + pagination.limit;
    const totalList = isFilter ? filteredTableData : subscribedDomainInfo.dataList;
    tableData.value = totalList.slice(start, end);
  };

  watch(
    () => subscribedDomainInfo.dataList,
    () => {
      refreshTableData();
      pagination.count = subscribedDomainInfo.dataList.length;
    },
    {
      immediate: true,
    },
  );

  // 告警级别修改
  const handleAlarmLevelChange = (row: IRowData, data: number[]) => {
    const params = {
      alert_level: data,
      bk_biz_id: row.bk_biz_id,
      clusters: [
        {
          cluster_domain: row.master_domain,
          cluster_type: row.cluster_type,
        },
      ],
      notice_ways: row.notice_ways,
    };
    runSaveSubscribe(params);
  };

  // 通知渠道修改
  const handleNotifyChannelChange = (row: IRowData, data: string[]) => {
    const params = {
      alert_level: row.alert_severity,
      bk_biz_id: row.bk_biz_id,
      clusters: [
        {
          cluster_domain: row.master_domain,
          cluster_type: row.cluster_type,
        },
      ],
      notice_ways: data,
    };
    runSaveSubscribe(params);
  };

  // 确认删除
  const handleConfirmDelete = (id: number) => {
    runDeleteSubscribe({ ids: [id] });
  };

  const handleFilterChange = (payload: TableChangeData) => {
    pagination.current = 1;
    if (!Object.keys(payload.filter!).length) {
      // 重置
      refreshTableData();
      return;
    }

    filteredTableData = subscribedDomainInfo.dataList.filter((item) =>
      Object.entries(payload.filter!).every(([key, value]) => {
        return (item as Record<string, unknown>)[key] === value;
      }),
    );
    refreshTableData(true);
  };

  // 切换当前页全选
  const handleTogglePageSelect = (checked: boolean) => {
    isCurrentPageAllSelected.value = checked;
    isWholeChecked.value = false;
    if (checked) {
      tableData.value.forEach((item) => {
        rowSelectMemo.value[item.id] = item;
      });
    } else {
      rowSelectMemo.value = {};
    }
  };

  // 切换跨页全选
  const handleToggleWholeSelect = (checked: boolean) => {
    isWholeChecked.value = checked;
    isCurrentPageAllSelected.value = false;
    if (checked) {
      subscribedDomainInfo.dataList.forEach((item) => {
        rowSelectMemo.value[item.id] = item;
      });
    } else {
      rowSelectMemo.value = {};
    }
  };

  // 多选
  const handleSelectionChange = (data: IRowData) => {
    if (rowSelectMemo.value[data.id]) {
      delete rowSelectMemo.value[data.id];
      isCurrentPageAllSelected.value = false;
      isWholeChecked.value = false;
    } else {
      rowSelectMemo.value[data.id] = data;
    }
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    refreshTableData();
  };

  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    refreshTableData();
  };

  // 编辑单个订阅
  const handleEditSubscription = (row: IRowData) => {
    currentRowData.value = row;
    isShowEditSingleSubscription.value = true;
  };

  // 新开tab跳转集群详情页
  const handleGoClusterDetailPage = (row: IRowData) => {
    const routeInfo = router.resolve({
      name: clusterTypeListPageMap[row.cluster_type],
      params: {
        clusterId: row.cluster_id,
      },
    });
    window.open(routeInfo.href);
  };

  onMounted(() => {
    const maxHeight = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 80;
    tableMaxHeight.value = maxHeight;
    pagination.limit = Math.floor((maxHeight - 85) / 40);
    for (let i = 0; i < pagination.limitList.length; i++) {
      if (pagination.limitList[i] > pagination.limit) {
        pagination.limitList.splice(i, 0, pagination.limit);
        break;
      }
    }
  });
</script>
<style lang="less">
  .my-alarm-subscription-page {
    padding: 16px;

    .top-operation-main {
      display: flex;
      justify-content: space-between;
      margin-bottom: 10px;

      .batch-operations {
        display: flex;
        gap: 8px;
      }
    }

    .table-main {
      .alarm-level-column {
        gap: 24px;

        .bk-checkbox {
          .bk-checkbox-label {
            width: auto;
          }
        }
      }

      .notify-channel-column {
        gap: 24px;

        .bk-checkbox {
          .bk-checkbox-label {
            width: auto;
          }
        }
      }

      .alarm-subscription-table {
        .t-table__header {
          th {
            &:not(:last-child) {
              border-right: 1px solid #f0f1f5 !important;
            }

            border-top: none !important;
          }
        }
      }

      .table-selection-head {
        position: relative;
        display: flex;
        align-items: center;

        .db-table-whole-check {
          position: relative;
          display: inline-block;
          width: 16px;
          height: 16px;
          vertical-align: middle;
          cursor: pointer;
          background-color: #fff;
          border: 1px solid #3a84ff;
          border-radius: 2px;

          &::after {
            position: absolute;
            top: 1px;
            left: 4px;
            width: 4px;
            height: 8px;
            border: 2px solid #3a84ff;
            border-top: 0;
            border-left: 0;
            content: '';
            transform: rotate(45deg);
          }
        }

        .select-menu-flag {
          margin-left: 4px;
          font-size: 18px;
          color: #63656e;
        }
      }

      .table-footer {
        // position: relative;
        // z-index: 1;
        display: flex;
        height: 60px;
        padding: 0 16px;
        // margin-top: -1px;
        background: #fff;
        // border-top: 1px solid var(--td-component-border);
        align-items: center;

        .bk-pagination {
          width: 100%;

          & > .is-last {
            margin-left: auto;
          }
        }
      }
    }
  }

  [data-theme~='ticket-table-select-menu'] {
    padding: 0 !important;

    .select-menu {
      padding: 5px 0;

      .select-menu-item {
        padding: 0 10px;
        font-size: 12px;
        line-height: 26px;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
          background-color: #eaf3ff;
        }

        &.is-selected {
          color: #3a84ff;
          background-color: #f4f6fa;
        }
      }
    }
  }

  .delete-subscription-pop-confirm {
    .bk-pop-confirm-footer {
      button {
        width: 64px;
      }
    }
  }

  .alarm-subscription-table-row {
    td {
      padding: 8.5px 16px !important;
    }
  }
</style>
