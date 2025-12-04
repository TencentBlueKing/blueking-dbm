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
    <div
      ref="tableWrapper"
      class="replenish-ticket-view">
      <PrimaryTable
        :data="tableData"
        :height="tableHeight"
        row-key="id"
        title-ellipsis>
        <TableColumn
          col-key="ids"
          fixed="left"
          :title="t('单号')"
          width="80">
          <template #default="{ row }: { row: IRowData }">
            <AuthRouterLink
              action-id="ticket_view"
              :permission="row.permission.ticket_view"
              :resource="row.id"
              target="_blank"
              :to="{
                name: 'ticketDetail',
                params: {
                  ticketId: row.id,
                },
              }"
              @click="(event: MouseEvent) => handleGoDetail(row, event)">
              {{ row.id }}
            </AuthRouterLink>
          </template>
        </TableColumn>
        <TableColumn
          col-key="ticket_type__in"
          :title="t('子任务')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            <template v-if="ticketInnerFlowInfo[row.id]">
              <div
                v-for="(flowItem, index) in ticketInnerFlowInfo[row.id]"
                :key="index"
                style="line-height: 26px">
                <BkButton
                  text
                  theme="primary"
                  @click="() => handleGoTaskHistoryDetail(row, flowItem)">
                  {{ flowItem.flow_alias }}
                </BkButton>
              </div>
              <span v-if="ticketInnerFlowInfo[row.id]!.length < 1">--</span>
            </template>
            <div
              v-else
              class="rotate-loading"
              style="display: inline-block">
              <DbIcon
                svg
                type="sync-pending" />
            </div>
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :title="t('状态')"
          width="180">
          <template #default="{ row }: { row: IRowData }">
            <TicketStatusTag
              v-if="row"
              :data="row" />
          </template>
        </TableColumn>
        <!-- <TableColumn
          col-key="db_type"
          :title="t('DB 类型')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            {{ dbNameMap[ticketDetailsInfo[row.id]?.db_type] || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="spec.spec_machine_type"
          :title="t('规格类型')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            {{ machineTypeMap[ticketDetailsInfo[row.id]?.spec?.spec_machine_type] || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="spec.spec_name"
          :title="t('规格')"
          width="180">
          <template #default="{ row }: { row: IRowData }">
            {{ ticketDetailsInfo[row.id]?.spec?.spec_name || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="city"
          :title="t('地域')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            {{ ticketDetailsInfo[row.id]?.city || '--' }}
          </template>
        </TableColumn> -->
        <!-- <TableColumn
          col-key="subzone"
          :title="t('园区')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            {{ ticketDetailsInfo[row.id]?.subzone || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="os_name"
          :title="t('操作系统')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            {{ ticketDetailsInfo[row.id]?.os_name || '--' }}
          </template>
        </TableColumn> -->
        <!-- <TableColumn
          col-key="count"
          :title="t('申请数量')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            <span class="bold-number">{{ ticketDetailsInfo[row.id]?.count || 0 }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="apply_count"
          :title="t('已交付')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            <span
              class="bold-number"
              :class="{
                'green-number': ticketApplyCount[row.id]?.delivery_count === ticketApplyCount[row.id]?.apply_count,
                'red-number': ticketApplyCount[row.id]?.delivery_count < ticketApplyCount[row.id]?.apply_count,
              }">
              {{ ticketApplyCount[row.id]?.delivery_count || 0 }}
            </span>
          </template>
        </TableColumn> -->
        <!-- <TableColumn
          col-key="id"
          :title="t('已导入')"
          width="150">
          <template #default="{ row }: { row: IRowData }">
            <span class="bold-number red-number">
              <span class="bold-number">{{ ticketDetailsInfo[row.id]?.count || 0 }}</span>
            </span>
          </template>
        </TableColumn> -->
        <!-- <TableColumn
          col-key="creator"
          :title="t('申请人')"
          width="150">
          <template #default="{ row }: { row: IRowData }">
            <span>{{ ticketDetailsInfo[row.id]?.operator || '--' }}</span>
          </template>
        </TableColumn> -->
        <TableColumn
          col-key="create_at"
          :title="t('申请时间')"
          width="220">
          <template #default="{ row }: { row: IRowData }">
            <span>{{ row.create_at ? utcDisplayTime(row.create_at) : '--' }}</span>
          </template>
        </TableColumn>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          @change="handlePageValueChange"
          @limit-change="handlePageLimitChange" />
      </div>
    </div>
    <TableDetailDialog
      v-model="isShowDetail"
      :default-offset-left="300"
      :min-width="900"
      @close="handleDetailDialogClose">
      <TicketDetail
        v-if="ticketId"
        :ticket-id="ticketId" />
    </TableDetailDialog>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  // import type ReplenishModel from '@services/model/db-resource/Replenish';
  import TicketModel from '@services/model/ticket/ticket';
  import { listTicketApplyInfo } from '@services/source/dbresourceReplenish';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  import { useUrlSearch } from '@hooks';

  import { DBTypeInfos } from '@common/const';

  import TicketDetail from '@components/ticket-detail/index.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { getBusinessHref, getOffset, utcDisplayTime } from '@utils';

  import useFetchData from './hooks/use-fetch-data';

  interface IRowData extends TicketModel {
    apply_count: number;
    city: string;
    count: number;
    create_at: string;
    db_type: string;
    delivery_count: number;
    id: number;
    operator: string;
    os_name: string;
    spec: {
      spec_machine_type: string;
      spec_name: string;
    };
    subzone: string;
  }

  const { t } = useI18n();
  const router = useRouter();
  const rootRef = useTemplateRef('tableWrapper');
  const { getSearchParams } = useUrlSearch();

  const {
    dataList,
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading: isLoading,
    pagination,
  } = useFetchData();

  const tableHeight = ref<number | 'auto'>('auto');
  const ticketId = ref<number>();
  const isShowDetail = ref(false);
  const ticketInnerFlowInfo = shallowRef<ServiceReturnType<typeof getInnerFlowInfo>>({});
  // const ticketApplyInfo = shallowRef<ServiceReturnType<typeof listTicketApplyInfo>>({});
  const tableData = shallowRef<IRowData[]>([]);

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${machine.label}`;
    });
  });

  watch(dataList, () => {
    if (dataList.value.length < 1) {
      return;
    }
    const ticketIds = dataList.value.map((item) => item.id).join(',');

    // 使用 Promise.all 处理多个异步请求
    Promise.all([getInnerFlowInfo({ ticket_ids: ticketIds }), listTicketApplyInfo({ ticket_ids: ticketIds })]).then(
      ([innerFlowInfo, applyInfo]) => {
        // 更新子任务信息
        ticketInnerFlowInfo.value = innerFlowInfo;

        console.log(applyInfo, dataList.value, 'wwwww');

        // tableData.value = dataList.value.map((item) => {
        //   const applyInfoItem = applyInfo.find((applyInfoItem) => applyInfoItem.id === item.id);
        //   return {
        //     ...item,
        //     apply_count: applyInfoItem?.apply_count || 0,
        //     delivery_count: applyInfoItem?.delivery_count || 0,
        //   };
        // });
      },
    );
  });

  const handleGoDetail = (ticketData: TicketModel, event: MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      return true;
    }

    event.preventDefault();
    event.stopPropagation();

    ticketId.value = ticketData.id;
    isShowDetail.value = true;
    router.replace({
      params: {
        ticketId: ticketData.id,
      },
      query: getSearchParams(),
    });
    return false;
  };

  const handleGoTaskHistoryDetail = (
    ticketData: TicketModel,
    data: ServiceReturnType<typeof getInnerFlowInfo>[number][number],
  ) => {
    const { href } = router.resolve({
      name: 'taskHistoryDetail',
      params: {
        root_id: data.flow_id,
      },
    });

    window.open(getBusinessHref(href, ticketData.bk_biz_id));
  };

  const handleDetailDialogClose = () => {
    ticketId.value = 0;
    router.replace({
      params: {
        ticketId: 0,
      },
      query: getSearchParams(),
    });
  };

  onMounted(() => {
    setTimeout(() => {
      tableHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 80;
    });
    handlePageValueChange(1);
  });

  defineExpose({
    fetchData,
  });
</script>
<style lang="less">
  .replenish-confirm-tip {
    background: #f5f7fa;
    border-radius: 2px;
    font-size: 14px;
    color: #4d4f56;
    letter-spacing: 0;
    width: 100%;
    line-height: 22px;
    padding: 12px 16px;
  }
</style>
