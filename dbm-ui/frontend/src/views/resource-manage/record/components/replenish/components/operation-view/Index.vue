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
      class="replenish-operation-view">
      <PrimaryTable
        :data="tableData"
        :height="tableHeight"
        row-key="id"
        title-ellipsis>
        <TableColumn
          col-key="id"
          fixed="left"
          title="ID"
          width="80">
          <template #default="{ row }: { row: IRowData }">
            <BkButton
              text
              theme="primary"
              @click="handleViewDetail(row)">
              {{ row.id }}
            </BkButton>
          </template>
        </TableColumn>
        <TableColumn
          col-key="details"
          :title="t('补货数量')"
          width="200">
          <template #default="{ row }: { row: IRowData }">
            <BkTag
              v-for="[db, value] in Object.entries(row.details).slice(0, MAX_DISPLAY_NUM)"
              :key="db"
              class="mr-4">
              {{ dbNameMap[db] }} : {{ value }}
            </BkTag>
            <BkTag
              v-if="Object.keys(row.details).length > MAX_DISPLAY_NUM"
              v-bk-tooltips="{
                content: Object.entries(row.details)
                  .slice(MAX_DISPLAY_NUM)
                  .map(([db, value]) => `${dbNameMap[db]} : ${value}`)
                  .join(', '),
                placement: 'top',
              }"
              class="mr-4">
              {{ `+${Object.keys(row.details).length - MAX_DISPLAY_NUM}` }}
            </BkTag>
          </template>
        </TableColumn>
        <TableColumn
          col-key="creator"
          :title="t('申请人')"
          width="120">
          <template #default="{ row }: { row: IRowData }">
            {{ row.creator || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="create_at"
          :title="t('申请时间')"
          width="200">
          <template #default="{ row }: { row: IRowData }">
            {{ row.create_at ? utcDisplayTime(row.create_at) : '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="status"
          :title="t('关联单据状态')"
          width="200">
          <template #default="{ row }: { row: IRowData }">
            <div
              v-bk-tooltips="{
                content: generateStatusCount(row.status)
                  .map((item) => `${item.text} ${item.count}`)
                  .join('，'),
                placement: 'top',
                disabled: generateStatusCount(row.status).length <= MAX_DISPLAY_NUM,
              }"
              class="ticket-status-list">
              <span
                v-for="(item, index) in generateStatusCount(row.status)"
                :key="item.text">
                {{ item.text }}
                <span
                  class="bold-number"
                  :style="{ color: item.color }">
                  {{ item.count }}
                </span>
                <span v-if="index < generateStatusCount(row.status).length - 1">，</span>
              </span>
            </div>
          </template>
        </TableColumn>
        <TableColumn
          col-key="operate"
          fixed="right"
          :title="t('操作')"
          width="100">
          <template #default="{ row }: { row: IRowData }">
            <BkButton
              text
              theme="primary"
              @click="handleViewDetail(row)">
              {{ t('查看明细') }}
            </BkButton>
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
    <Details
      v-if="detailsData"
      v-model:is-show="isShowDetails"
      :data="detailsData" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { DBTypeInfos } from '@common/const';

  import { getOffset, utcDisplayTime } from '@utils';

  import Details from './components/Details.vue';
  import useFetchData from './hooks/use-fetch-data';

  type IRowData = NonNullable<(typeof tableData.value)[0]>;

  const { t } = useI18n();
  const rootRef = useTemplateRef('tableWrapper');

  const {
    fetchData,
    handlePageLimitChange,
    handlePageValueChange,
    loading: isLoading,
    pagination,
    tableData,
  } = useFetchData();

  const MAX_DISPLAY_NUM = 4;

  const colorMap = {
    [TicketModel.STATUS_APPROVE]: '#267BCF',
    [TicketModel.STATUS_FAILED]: '#EA3636',
    [TicketModel.STATUS_INNER_TODO]: '#E38B02',
    [TicketModel.STATUS_RESOURCE_REPLENISH]: '#F59500',
    [TicketModel.STATUS_RUNNING]: '#3A84FF',
    [TicketModel.STATUS_SUCCEEDED]: '#2CAF5E',
    [TicketModel.STATUS_TERMINATED]: '#E71818',
    [TicketModel.STATUS_TIMER]: '#3F726F',
    [TicketModel.STATUS_TODO]: '#4D4F56',
  };

  const generateStatusCount = (status: string[]) => {
    return status.reduce<Array<{ color: string; count: number; text: string }>>((acc, curr) => {
      const text = TicketModel.statusTextMap[curr as keyof typeof TicketModel.statusTextMap] || '--';
      const color = colorMap[curr] || '#63656e';
      const existing = acc.find((item) => item.color === color);
      if (existing) {
        existing.count += 1;
      } else {
        acc.push({ color, count: 1, text });
      }
      return acc;
    }, []);
  };

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${db.name} - ${machine.label}`;
    });
  });

  const tableHeight = ref<number | 'auto'>('auto');
  const isShowDetails = ref(false);
  const detailsData = ref<IRowData>();

  const handleViewDetail = (data: IRowData) => {
    isShowDetails.value = true;
    detailsData.value = data;
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
  .replenish-operation-view {
    .ticket-status-list {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
