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
  <div class="redis-struct-ins-page">
    <BkAlert
      closable
      theme="info"
      :title="t('数据复制记录：数据复制记录提供数据复制后相关操作')" />
    <div class="top-operate">
      <BkInput
        v-model="searchValue"
        clearable
        :placeholder="t('请输入集群名称')"
        style="width: 500px; margin-bottom: 16px"
        type="search"
        @clear="handleClickSearch"
        @enter="handleClickSearch" />
      <DatePicker
        v-model="dateTimeRange"
        behavior="normal"
        :disabled="false"
        :version="2"
        @update:model-value="handleValueChange" />
    </div>
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <PrimaryTable
        :bk-ui-settings="settings"
        class="table-box"
        :columns="columns"
        :data="tableData"
        :max-height="tableHeight"
        row-key="id">
        <template #empty>
          <EmptyStatus
            :is-anomalies="false"
            :is-searching="!!searchValue"
            @clear-search="handleClearSearch"
            @refresh="fetchHostNodes" />
        </template>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          :model-value="pagination.current"
          @change="handleChangePage"
          @limit-change="handeChangeLimit" />
      </div>
    </BkLoading>
    <DataCopyTransferDetail
      :data="currentActiveRow"
      :is-show="isShowDataCopyTransferDetail"
      @on-close="() => (isShowDataCopyTransferDetail = false)" />
    <!-- <BkDialog
      class="recopy-dialog"
      dialog-type="show"
      header-align="center"
      :is-show="showRecopyDialog"
      :title="t('确认重新复制数据？')">
      <div class="content-box">
        <div class="title-spot">
          {{ t('复制类型') }}<span class="required" />
        </div>
        <BkRadioGroup
          v-model="copyType"
          class="radios">
          <BkRadio
            v-for="item in copyTypeList"
            :key="item.value"
            :label="item.value">
            {{ item.label }}
          </BkRadio>
        </BkRadioGroup>
        <div class="btn-box">
          <BkButton
            class="w-88"
            theme="primary"
            @click="handleClickConfirmRecopy">
            重新复制
          </BkButton>
          <BkButton
            class="w-88 ml-8"
            @click="handleClickCancelRecopy">
            取消
          </BkButton>
        </div>
      </div>
    </BkDialog> -->
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { Dayjs } from 'dayjs';
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import DatePicker, { DateRange, type DateValue } from '@blueking/date-picker';

  import RedisDSTHistoryJobModel, { CopyModes, TransmissionTypes } from '@services/model/redis/redis-dst-history-job';
  import { getRedisDTSHistoryJobs, setJobDisconnectSync } from '@services/source/redisDts';

  import { useDefaultPagination } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import useResetTableHeight from '@views/db-manage/redis/common/hooks/useResetTableHeight';

  import { utcDisplayTime } from '@utils';

  import DataCopyTransferDetail from './components/DataCopyTransferDetail.vue';
  import ExecuteStatus from './components/ExecuteStatus.vue';
  import KeyTags from './components/KeyTags.vue';

  const { t } = useI18n();
  const router = useRouter();

  const datePickerFormat = 'YYYY-MM-DDTHH:mm:ssZ';

  const generateUTCDateTime = (value?: [string, string]) =>
    new DateRange(value ? value : dateTimeRange.value, datePickerFormat)
      .toEmitValue()[1]
      .map((item) => item.formatText) as [string, string];

  const tableData = ref<RedisDSTHistoryJobModel[]>([]);
  const isTableDataLoading = ref(false);
  const isShowDataCopyTransferDetail = ref(false);
  const currentActiveRow = ref<RedisDSTHistoryJobModel>();
  const searchValue = ref('');
  const dateTimeRange = ref<[string, string]>(['now-30d/d', 'now']);
  const dateTimeRangeUTC = ref(generateUTCDateTime());
  const timer = ref();
  const tableHeight = ref(500);
  const pagination = ref(useDefaultPagination());
  const searchTimer = ref();

  const settings = {
    checked: [
      'src_cluster',
      'dst_cluster',
      'dts_copy_type',
      'key_white_regex',
      'key_black_regex',
      'bill_id',
      'update_time',
      'status',
      'create_time',
    ],
    fields: [
      {
        field: 'src_cluster',
        label: t('源集群'),
      },
      {
        field: 'dst_cluster',
        label: t('目标集群'),
      },
      {
        field: 'dts_copy_type',
        label: t('复制类型'),
      },
      {
        field: 'key_white_regex',
        label: t('包含 key'),
      },
      {
        field: 'key_black_regex',
        label: t('排除 key'),
      },
      {
        field: 'bill_id',
        label: t('关联单据'),
      },
      {
        field: 'update_time',
        label: t('最近一次修复单'),
      },
      {
        field: 'status',
        label: t('状态'),
      },
      {
        field: 'create_time',
        label: t('创建时间'),
      },
    ],
  };

  const copyTypesMap = {
    [CopyModes.COPY_FROM_ROLLBACK_INSTANCE]: t('构造实例至业务内'),
    [CopyModes.COPY_FROM_ROLLBACK_TEMP]: t('从回滚临时环境复制数据'),
    [CopyModes.CROSS_BISNESS]: t('跨业务'),
    [CopyModes.INTRA_BISNESS]: t('业务内'),
    [CopyModes.INTRA_TO_THIRD]: t('业务内至第三方'),
    [CopyModes.SELFBUILT_TO_INTRA]: t('自建集群至业务内'),
    REDIS_CLUSTER_SHARD_NUM_UPDATE: t('集群分片变更'),
    REDIS_CLUSTER_TYPE_UPDATE: t('集群类型变更'),
  };

  // 渲染操作区按钮
  // 1. "断开同步" 按钮: 只要 有处于 running_cnt >0，pending_exec_cnt >0 就代表，还有运行中 or 待执行的 task，"断开同步" 需要显示；
  // 2. "重新复制" 按钮：可以限制只有处于 "传输已完成"、"传输被终止" 状态的 任务，才点亮；
  // 3. "断开同步" 点击  到  "重新复制" 点亮，是有一个时间延迟的，因为是异步操作；
  const renderOperation = (data: RedisDSTHistoryJobModel, index: number) => {
    let showDisconnect = false;
    let showDataCheckAndRepair = false;
    let showRecopy = false;
    if (data.running_cnt > 0 || data.pending_exec_cnt > 0) {
      showDisconnect = true;
    }
    switch (data.status) {
      case TransmissionTypes.INCREMENTAL_TRANSFERING: // 增量传输中
        showDataCheckAndRepair = true;
        break;
      case TransmissionTypes.END_OF_TRANSMISSION: // 传输结束
        showRecopy = true;
        break;
      case TransmissionTypes.TRANSSION_TERMINATE: // 传输终止
        showRecopy = true;
        break;
      default:
        break;
    }

    return (
      <div style="color:#3A84FF;cursor:pointer;'">
        {showRecopy ? (
          <bk-button
            text
            theme='primary'
            onClick={() => handleClickRecopy(data)}>
            {t('重新复制')}
          </bk-button>
        ) : (
          <>
            <bk-button
              style={{ color: showDisconnect ? '#3A84FF' : '#C4C6CC' }}
              text
              theme='primary'
              onClick={() => handleClickDisconnectSync(data, index, showDisconnect)}>
              {t('断开同步')}
            </bk-button>
            <bk-button
              style={{ color: showDataCheckAndRepair ? '#3A84FF' : '#C4C6CC', marginLeft: '10px' }}
              text
              theme='primary'
              onClick={() => handleClickDataCheckAndRepair(data, showDataCheckAndRepair)}>
              {t('数据校验与修复')}
            </bk-button>
          </>
        )}
      </div>
    );
  };

  const columns: PrimaryTableCol[] = [
    {
      cell: (_, { row }) => (
        <span
          style='color:#3A84FF;cursor:pointer;'
          onClick={() => handleClickOpenTransferDetail(row as RedisDSTHistoryJobModel)}>
          {row.src_cluster}
        </span>
      ),
      colKey: 'src_cluster',
      minWidth: 220,
      title: t('源集群'),
    },
    {
      colKey: 'dst_cluster',
      minWidth: 220,
      title: t('目标集群'),
    },
    {
      cell: (_, { row }) => <span>{copyTypesMap[row.dts_copy_type as keyof typeof copyTypesMap]}</span>,
      colKey: 'dts_copy_type',
      filter: {
        list: [
          { label: t('业务内'), value: CopyModes.INTRA_BISNESS },
          { label: t('跨业务'), value: CopyModes.CROSS_BISNESS },
          { label: t('业务内至第三方'), value: CopyModes.INTRA_TO_THIRD },
          { label: t('自建集群至业务内'), value: CopyModes.SELFBUILT_TO_INTRA },
        ],
        showConfirmAndReset: true,
        type: 'multiple',
      },
      title: t('复制类型'),
      width: 120,
    },
    {
      cell: (_, { row }) => {
        if (row.key_white_regex) {
          const tags = row.key_white_regex.split('\n');
          return (
            <KeyTags
              data={tags}
              maxRow={2}
            />
          );
        }
        return <span>--</span>;
      },
      colKey: 'key_white_regex',
      ellipsis: false,
      minWidth: 250,
      title: t('包含 key'),
    },
    {
      cell: (_, { row }) => {
        if (row.key_black_regex) {
          const tags = row.key_black_regex.split('\n');
          return <KeyTags data={tags} />;
        }
        return <span>--</span>;
      },
      colKey: 'key_black_regex',
      ellipsis: true,
      minWidth: 250,
      title: t('排除 key'),
    },
    {
      cell: (_, { row }) =>
        row.bill_id ? (
          <router-link
            target='_blank'
            to={{
              name: 'bizTicketManage',
              params: {
                ticketId: row.bill_id,
              },
            }}>
            {row.bill_id}
          </router-link>
        ) : (
          '--'
        ),
      colKey: 'bill_id',
      ellipsis: true,
      title: t('关联单据'),
      width: 120,
    },
    {
      cell: (_, { row }) => <span>{utcDisplayTime(row.update_time)}</span>,
      colKey: 'update_time',
      ellipsis: true,
      title: t('最近一次修复单'),
      width: 120,
    },
    {
      cell: (_, { row }) => <ExecuteStatus type={row.status} />,
      colKey: 'status',
      ellipsis: true,
      title: t('状态'),
      width: 120,
    },
    {
      cell: (_, { row }) => <span>{utcDisplayTime(row.create_time)}</span>,
      colKey: 'create_time',
      ellipsis: true,
      title: t('创建时间'),
      width: 180,
    },
    {
      cell: (_, { row, rowIndex }) => renderOperation(row as RedisDSTHistoryJobModel, rowIndex),
      colKey: 'row-operation',
      ellipsis: true,
      fixed: 'right',
      title: t('操作'),
      width: 180,
    },
  ];

  watch(searchValue, () => {
    clearTimeout(searchTimer.value);
    searchTimer.value = setTimeout(() => {
      fetchHostNodes();
    }, 500);
  });

  const { resetTableHeight } = useResetTableHeight(tableHeight, 275);

  onMounted(() => {
    timer.value = setTimeout(() => {
      fetchHostNodes();
    }, 5000);
    resetTableHeight();
  });

  onBeforeUnmount(() => {
    clearTimeout(timer.value);
  });

  // const copyTypeList = [
  //   {
  //     label: t('全量覆盖同名 Key（如：del  $key+ hset $key）'),
  //     value: 0,
  //   },
  //   {
  //     label: t('增量覆盖同名 Key（如：hset $key）'),
  //     value: 1,
  //   },
  //   {
  //     label: t('清空目标集群所有数据'),
  //     value: 2,
  //   },
  // ];

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    fetchHostNodes();
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    pagination.value.current = 1;
    fetchHostNodes();
  };

  const handleClickSearch = () => {
    fetchHostNodes();
  };

  const handleClearSearch = () => {
    searchValue.value = '';
  };

  const fetchHostNodes = async () => {
    if (!dateTimeRangeUTC.value[0]) {
      return;
    }
    const ret = await getRedisDTSHistoryJobs({
      cluster_name: searchValue.value,
      end_time: dateTimeRangeUTC.value[1],
      page: pagination.value.current,
      page_size: pagination.value.limit,
      start_time: dateTimeRangeUTC.value[0],
    });
    tableData.value = ret.jobs;
    pagination.value.count = ret.total_cnt;
  };

  fetchHostNodes();

  const handleValueChange = (
    _value: DateValue | undefined,
    info: { dayjs: Dayjs | null; formatText: string | null }[],
  ) => {
    const [startInfo, endInfo] = info;
    if (!startInfo?.formatText || !endInfo?.formatText) {
      return;
    }
    const { formatText: startDate } = startInfo;
    const { formatText: endDate } = endInfo;
    dateTimeRangeUTC.value = generateUTCDateTime([startDate, endDate]);
    nextTick(() => {
      fetchHostNodes();
    });
  };

  const handleClickOpenTransferDetail = (row: RedisDSTHistoryJobModel) => {
    currentActiveRow.value = row;
    isShowDataCopyTransferDetail.value = true;
  };

  const handleClickDisconnectSync = (row: RedisDSTHistoryJobModel, index: number, isAvailable: boolean) => {
    if (!isAvailable) {
      return;
    }
    InfoBox({
      confirmText: '断开同步',
      onConfirm: async () => {
        await setJobDisconnectSync({
          bill_id: row.bill_id,
          dst_cluster: row.dst_cluster,
          src_cluster: row.src_cluster,
        });
        if (row.status === TransmissionTypes.INCREMENTAL_TRANSFERING) {
          tableData.value[index].status = TransmissionTypes.END_OF_TRANSMISSION;
        } else {
          tableData.value[index].status = TransmissionTypes.TRANSSION_TERMINATE;
        }
      },
      subTitle: t('断开后，数据将不会再再自动同步，请谨慎操作！'),
      title: t('确认断开同步？'),
      width: 420,
    });
  };

  const handleClickDataCheckAndRepair = (row: RedisDSTHistoryJobModel, isAvailable: boolean) => {
    if (!isAvailable) {
      return;
    }
    router.push({
      name: TicketTypes.REDIS_DATACOPY_CHECK_REPAIR,
      query: {
        historyJobId: row.id,
      },
    });
  };

  const handleClickRecopy = (row: RedisDSTHistoryJobModel) => {
    router.push({
      name: TicketTypes.REDIS_CLUSTER_DATA_COPY,
      query: {
        historyJobId: row.id,
      },
    });
  };

  // const handleClickConfirmRecopy = () => {
  //   console.log(currentActiveRow.value);
  // };

  // const handleClickCancelRecopy = () => {
  //   showRecopyDialog.value = false;
  // };
</script>

<style lang="less" scoped>
  .table-box {
    :deep(.key-tag) {
      display: inline-flex;
      height: 22px;
      padding: 0 10px;
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      text-align: center;
      background: #f0f1f5;
      border-radius: 2px;
    }
  }

  .normal-color {
    td {
      .t-table__cell {
        color: #63656e !important;
      }
    }
  }

  .disable-color {
    td {
      .t-table__cell {
        color: #c4c6cc !important;
      }
    }
  }

  .operate-box {
    display: flex;
    width: 180px;
    justify-content: space-between;

    span {
      cursor: pointer;
    }
  }

  .redis-struct-ins-page {
    padding-bottom: 20px;

    .table-footer {
      display: flex;
      margin-top: 12px;
      justify-content: flex-end;
    }

    .top-operate {
      display: flex;
      width: 100%;
      gap: 20px;
      margin-top: 16px;

      .time-picker {
        width: 380px;
      }
    }

    .buttons {
      margin: 16px 0;
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }

  .content-box {
    display: flex;
    width: 100%;
    flex-direction: column;

    .radios {
      display: flex;
      width: 100%;
      flex-direction: column;

      :deep(.bk-radio) {
        margin: 12px 0;
      }
    }

    .btn-box {
      display: flex;
      width: 100%;
      justify-content: center;
      margin-top: 22px;
    }
  }
</style>
