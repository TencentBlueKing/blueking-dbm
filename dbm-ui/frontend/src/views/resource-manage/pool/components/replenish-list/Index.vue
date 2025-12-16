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
  <div class="resource-pool-replenish-list">
    <div class="top-operation mb-12">
      <div>
        <div style="display: none">
          <div ref="popRef">
            {{ t('补货正在进行中，') }}
            <BkButton
              text
              theme="primary"
              @click="handleForward">
              {{ t('跳转查看') }}
              <DbIcon
                class="ml-6"
                type="bk-dbm-icon db-icon-link" />
            </BkButton>
          </div>
        </div>
        <span ref="handleRef">
          <BkButton
            :disabled="isSubmitting || Boolean(runningReplenishRecord)"
            :loading="isSubmitting"
            theme="primary"
            @click="handleReplenish">
            <span v-if="!runningReplenishRecord">{{ t('一键补货') }}</span>
            <template v-else>
              <DbIcon
                class="mr-6"
                type="bk-dbm-icon db-icon-sync-pending" />
              {{ t('补货中') }}
            </template>
          </BkButton>
        </span>
        <DbIcon
          class="ml-16"
          type="bk-dbm-icon db-icon-dingshichufa" />
        {{ t('系统于每日 time 发起自动提交补货操作，也可手动点击', [flushTime]) }}
      </div>
      <div>
        <span>{{ t('最近更新时间：') }}{{ updateTime }}</span>
        <BkButton
          class="ml-8"
          @click="handleRefresh">
          <DbIcon
            class="mr-6"
            type="bk-dbm-icon db-icon-gengxin" />
          {{ t('更新数据') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleForwardRecord">
          <DbIcon
            class="mr-6"
            type="bk-dbm-icon db-icon-history-2" />
          {{ t('补货记录') }}
        </BkButton>
        <BkButton
          class="ml-8"
          :disabled="tableData.length === 0"
          @click="handleExport">
          <DbIcon
            class="mr-6"
            type="daochu" />
          {{ t('导出数据') }}
        </BkButton>
      </div>
    </div>
    <BkLoading :loading="isLoading">
      <div ref="tableWrapper">
        <PrimaryTable
          :data="tableData"
          :height="tableHeight"
          row-key="db_type"
          title-ellipsis>
          <TableColumn
            col-key="db_type"
            :title="t('DB 类型')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ dbNameMap[row.db_type] || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="spec_machine_type"
            :title="t('规格类型')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ machineTypeMap[row.spec_machine_type] || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="spec_name"
            :title="t('规格')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ row.spec_name || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="city"
            :title="t('地域')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ row.city || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="subzone"
            :title="t('园区')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ row.subzone || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="os_name"
            :title="t('操作系统')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ row.os_name || '--' }}
            </template>
          </TableColumn>
          <!-- <TableColumn
            col-key="machine_refer_count"
            width="120"
            :title="t('AI 预测水位（台）')">
            <template #default="{ row }: { row: IRowData }">
              <span class="bold-number">{{ row.machine_refer_count }}</span>
            </template>
          </TableColumn> -->
          <TableColumn
            col-key="machine_refer_count"
            :title="t('参考水位（台）')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              <span class="bold-number">{{ row.machine_refer_count }}</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="resource_count"
            :title="t('当前数量（台）')"
            width="120">
            <template #default="{ row }: { row: IRowData }">
              <span class="bold-number blue-number">{{ row.resource_count }}</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="resource_count"
            :title="t('待补充数量（台）')"
            width="150">
            <template #default="{ row }: { row: IRowData }">
              <span class="bold-number red-number">
                {{ Math.max(row.machine_refer_count - row.resource_count, 0) }}
              </span>
            </template>
          </TableColumn>
          <TableColumn
            v-if="isShowOperationColumn"
            col-key="operate"
            fixed="right"
            :title="t('操作')"
            width="100">
            <template #default="{ row }: { row: IRowData }">
              <BkButton
                text
                theme="primary"
                @click="handleReplenish(row)">
                {{ t('补货') }}
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
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import InfoBox from 'bkui-vue/lib/info-box';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createResourceReplenish } from '@services/source/dbresourceReplenish';

  import { useFunController, useSystemEnviron } from '@stores';

  import { DBTypeInfos } from '@common/const';

  import { exportExcelFile, getOffset, messageSuccess } from '@utils';

  import useFetchData from './hooks/use-fetch-data';

  type IRowData = NonNullable<(typeof tableData.value)[0]>;

  const { t } = useI18n();
  const rootRef = useTemplateRef('tableWrapper');
  const router = useRouter();
  const systemEnvironStore = useSystemEnviron();
  const funControllerStore = useFunController();
  const {
    dataList,
    flushTime,
    handlePageLimitChange,
    handlePageValueChange,
    loading: isLoading,
    pagination,
    run: fetchData,
    runningReplenishRecord,
    tableData,
    updateTime,
  } = useFetchData();

  const tableHeight = ref<number | 'auto'>('auto');
  const handleRef = ref();
  const popRef = ref();
  let tippyIns: Instance;
  const URL_REPLENISH_MEMO_KEY = '__replenish_operation_view_payload__';
  const isShowOperationColumn =
    funControllerStore.funControllerData?.resourceManage?.children?.replenishList.children?.replenishListRowOperation
      ?.is_enabled;

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[machine.value] = machine.label;
    });
  });

  const handleRefresh = () => {
    fetchData({
      cache: false,
    });
  };

  const handleForward = () => {
    router.push({
      name: 'resourceReplenishRecord',
      params: {
        page: 'operation-view',
      },
      query: {
        [URL_REPLENISH_MEMO_KEY]: encodeURIComponent(
          JSON.stringify({
            id: String(runningReplenishRecord.value),
          }),
        ),
      },
    });
  };

  const handleForwardRecord = () => {
    router.push({
      name: 'resourceReplenishRecord',
      params: {
        page: 'operation-view',
      },
    });
  };

  const handleExport = () => {
    /* eslint-disable */
    const formatData = dataList.value.map((row) => ({
      [t('DB 类型')]: dbNameMap[row.db_type],
      [t('规格类型')]: machineTypeMap[row.spec_machine_type],
      [t('规格')]: row.spec_name,
      [t('地域')]: row.city,
      [t('园区')]: row.subzone,
      [t('操作系统')]: row.os_name,
      [t('参考水位（台）')]: row.machine_refer_count,
      [t('当前数量（台）')]: row.resource_count,
      [t('待补充数量（台）')]: Math.max(row.machine_refer_count - row.resource_count, 0),
    }));
    /* eslint-enable */
    const colsWidths = Array(8)
      .fill(15)
      .map((width) => ({ width }));
    exportExcelFile(formatData, colsWidths, 'Sheet1', `${t('待补货列表')}_${updateTime.value}.xlsx`);
  };

  const { loading: isSubmitting, run: replenish } = useRequest(createResourceReplenish, {
    manual: true,
    onSuccess: () => {
      messageSuccess('手动补货单据已提交');
      handleRefresh();
    },
  });

  const handleReplenish = (rowData?: IRowData) => {
    const list = rowData ? [rowData] : dataList.value;

    const replenishList = list
      .filter((item) => item.resource_count < item.machine_refer_count)
      .map((item) => ({
        city: item.city,
        count: Math.max(item.machine_refer_count - item.resource_count, 0),
        db_type: item.db_type,
        os_name: item.os_name,
        spec_id: item.spec_id,
        subzone: item.subzone,
      }));
    const totalReplenish = replenishList.reduce((total, item) => total + item.count, 0);

    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认补货'),
      content: () => (
        <>
          <div style='text-align: left; padding: 0 24px;'>
            <p
              class='pt-12 replenish-confirm-tip'
              style='font-size: 12px;'>
              {t('确认后，将按照待补货列表发起补货操作')}
            </p>
          </div>
        </>
      ),
      onConfirm: () => {
        return replenish({
          bk_biz_id: systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ,
          infos: replenishList,
          remark: t('手动补货'),
        });
      },
      title: t('确认一键补货 n 台？', [totalReplenish]),
      type: 'warning',
    });
  };

  onActivated(() => {
    tableHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 140;
    fetchData({
      cache: true,
    });
  });

  watch(runningReplenishRecord, () => {
    if (runningReplenishRecord.value && handleRef.value && popRef.value) {
      tippyIns = tippy(handleRef.value as SingleTarget, {
        allowHTML: true,
        appendTo: () => document.body,
        arrow: true,
        content: popRef.value,
        hideOnClick: true,
        interactive: true,
        maxWidth: 'none',
        offset: [0, 8],
        placement: 'top',
        theme: 'black',
        trigger: 'mouseenter click',
        zIndex: 999999,
      });
    }
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });
</script>
<style lang="less">
  .resource-pool-replenish-list {
    padding: 16px 24px;
    font-family: MicrosoftYaHei;
    background: #fff;
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

    .top-operation {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .bold-number {
      font-family: MicrosoftYaHei-Bold;
      font-weight: 700;
      font-size: 12px;
      color: #4d4f56;
      letter-spacing: 0;
      line-height: 20px;
    }

    .blue-number {
      color: #3a84ff;
    }

    .red-number {
      color: #ea3636;
    }

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

      .bk-pagination {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }
  }

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
