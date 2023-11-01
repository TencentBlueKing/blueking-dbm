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
        style="width:500px;margin-bottom: 16px;"
        type="search"
        @clear="handleClickSearch"
        @enter="handleClickSearch" />
      <BkDatePicker
        ref="datePickerRef"
        append-to-body
        class="time-picker"
        clearable
        :model-value="dateTimeRange"
        type="datetimerange"
        @change="handlerChangeDatetime"
        @pick-success="handleConfirmDatetime" />
    </div>
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <DbOriginalTable
        class="table-box"
        :columns="columns"
        :data="tableData"
        :max-height="tableHeight"
        :pagination="pagination"
        remote-pagination
        :settings="settings"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchHostNodes" />
    </BkLoading>
    <DataCopyTransferDetail
      :data="currentActiveRow"
      :is-show="isShowDataCopyTransferDetail"
      @on-close="() => isShowDataCopyTransferDetail = false" />
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
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisDSTHistoryJobModel,
    {
      CopyModes,
      TransmissionTypes,
    } from '@services/model/redis/redis-dst-history-job';
  import {
    getRedisDTSHistoryJobs,
    setJobDisconnectSync,
  } from '@services/source/redisDts';

  import { useDefaultPagination } from '@hooks';

  import { LocalStorageKeys   } from '@common/const';

  import useResetTableHeight from '@views/redis/common/hooks/useResetTableHeight';
  import { formatDatetime } from '@views/redis/common/utils';

  import DataCopyTransferDetail from './components/DataCopyTransferDetail.vue';
  import ExecuteStatus from './components/ExecuteStatus.vue';
  import KeyTags from './components/KeyTags.vue';

  const { t } = useI18n();
  const router = useRouter();

  const tableData = ref<RedisDSTHistoryJobModel[]>([]);
  const isTableDataLoading = ref(false);
  const isShowDataCopyTransferDetail = ref(false);
  const currentActiveRow = ref<RedisDSTHistoryJobModel>();
  // const copyType = ref(0);
  // const showRecopyDialog = ref(false);
  const searchValue = ref('');
  const dateTimeRange = ref<[Date, Date]>([new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), new Date()]);
  const timer = ref();
  const tableHeight = ref(500);
  const pagination = ref(useDefaultPagination());
  const searchTimer = ref();

  const settings = {
    fields: [
      {
        label: t('源集群'),
        field: 'src_cluster',
      },
      {
        label: t('目标集群'),
        field: 'dst_cluster',
      },
      {
        label: t('复制类型'),
        field: 'dts_copy_type',
      },
      {
        label: t('包含 key'),
        field: 'key_white_regex',
      },
      {
        label: t('排除 key'),
        field: 'key_black_regex',
      },
      {
        label: t('关联单据'),
        field: 'bill_id',
      },
      {
        label: t('最近一次修复单'),
        field: 'update_time',
      },
      {
        label: t('状态'),
        field: 'status',
      },
      {
        label: t('创建时间'),
        field: 'create_time',
      },
    ],
    checked: ['src_cluster', 'dst_cluster', 'dts_copy_type', 'key_white_regex', 'key_black_regex', 'bill_id', 'update_time', 'status', 'create_time'],
  };

  const copyTypesMap = {
    [CopyModes.CROSS_BISNESS]: t('跨业务'),
    [CopyModes.INTRA_BISNESS]: t('业务内'),
    [CopyModes.INTRA_TO_THIRD]: t('业务内至第三方'),
    [CopyModes.SELFBUILT_TO_INTRA]: t('自建集群至业务内'),
    [CopyModes.COPY_FROM_ROLLBACK_INSTANCE]: t('构造实例至业务内'),
    [CopyModes.COPY_FROM_ROLLBACK_TEMP]: t('从回滚临时环境复制数据'),
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

    return (<div style="color:#3A84FF;cursor:pointer;'">
        {showRecopy
          ? <bk-button
              text
              theme="primary"
              onClick={() => handleClickRecopy(data)}>
              {t('重新复制')}
            </bk-button>
          : <>
            <bk-button
              text
              theme="primary"
              style={{ color: showDisconnect ? '#3A84FF' : '#C4C6CC' }}
              onClick={() => handleClickDisconnectSync(data, index, showDisconnect)}>
              {t('断开同步')}
              </bk-button>
            <bk-button
              text
              theme="primary"
              style={{ color: showDataCheckAndRepair ? '#3A84FF' : '#C4C6CC', marginLeft: '10px' }}
              onClick={() => handleClickDataCheckAndRepair(data, showDataCheckAndRepair)}>
              {t('数据校验与修复')}
            </bk-button>
            </>
        }
      </div>);
  };

  const columns = [
    {
      label: t('源集群'),
      field: 'src_cluster',
      minWidth: 220,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span style="color:#3A84FF;cursor:pointer;" onClick={() => handleClickOpenTransferDetail(data)}>{data.src_cluster}</span>,
    },
    {
      label: t('目标集群'),
      field: 'dst_cluster',
      minWidth: 220,
    },
    {
      label: t('复制类型'),
      filter: {
        list: [
          { text: t('业务内'), value: CopyModes.INTRA_BISNESS },
          { text: t('跨业务'), value: CopyModes.CROSS_BISNESS },
          { text: t('业务内至第三方'), value: CopyModes.INTRA_TO_THIRD },
          { text: t('自建集群至业务内'), value: CopyModes.SELFBUILT_TO_INTRA },
        ],
      },
      field: 'dts_copy_type',
      width: 120,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span>{copyTypesMap[data.dts_copy_type]}</span>,
    },
    {
      label: t('包含 key'),
      field: 'key_white_regex',
      showOverflowTooltip: false,
      width: 120,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => {
        if (data.key_white_regex) {
          const tags = data.key_white_regex.split('\n');
          return <KeyTags maxRow={2} data={tags} />;
        }
        return <span>--</span>;
      },
    },
    {
      label: t('排除 key'),
      field: 'key_black_regex',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => {
        if (data.key_black_regex) {
          const tags = data.key_black_regex.split('\n');
          return <KeyTags data={tags} />;
        }
        return <span>--</span>;
      },
    },
    {
      label: t('关联单据'),
      field: 'bill_id',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span style="color:#3A84FF;cursor:pointer;" onClick={() => handleClickRelatedTicket(data.bill_id)}>{data.bill_id}</span>,
    },
    {
      label: t('最近一次修复单'),
      field: 'update_time',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('状态'),
      field: 'status',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <ExecuteStatus type={data.status} />,
    },
    {
      label: t('创建时间'),
      field: 'create_time',
      showOverflowTooltip: true,
      width: 180,
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      showOverflowTooltip: true,
      width: 180,
      render: ({ index, data }: {index: number, data: RedisDSTHistoryJobModel}) => renderOperation(data, index),
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


  const fetchHostNodes = async () => {
    const ret = await getRedisDTSHistoryJobs({
      page: pagination.value.current,
      page_size: pagination.value.limit,
      start_time: formatDatetime(dateTimeRange.value[0]),
      end_time: formatDatetime(dateTimeRange.value[1]),
      cluster_name: searchValue.value,
    });
    tableData.value = ret.jobs;
    pagination.value.count = ret.total_cnt;
  };

  fetchHostNodes();

  const handlerChangeDatetime = (range: [Date, Date]) => {
    dateTimeRange.value = range;
  };

  const handleConfirmDatetime = () => {
    fetchHostNodes();
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
      title: t('确认断开同步？'),
      subTitle: t('断开后，数据将不会再再自动同步，请谨慎操作！'),
      width: 420,
      confirmText: '断开同步',
      onConfirm: async () => {
        await setJobDisconnectSync({
          bill_id: row.bill_id,
          src_cluster: row.src_cluster,
          dst_cluster: row.dst_cluster,
        });
        if (row.status === TransmissionTypes.INCREMENTAL_TRANSFERING) {
          tableData.value[index].status = TransmissionTypes.END_OF_TRANSMISSION;
        } else {
          tableData.value[index].status = TransmissionTypes.TRANSSION_TERMINATE;
        }
      } });
  };

  const handleClickDataCheckAndRepair = (row: RedisDSTHistoryJobModel, isAvailable: boolean) => {
    if (!isAvailable) {
      return;
    }
    localStorage.setItem(LocalStorageKeys.REDIS_DATA_CHECK_AND_REPAIR, JSON.stringify(row));
    router.push({
      name: 'RedisToolboxDataCheckRepair',
    });
  };


  const handleClickRecopy = (row: RedisDSTHistoryJobModel) => {
    localStorage.setItem(LocalStorageKeys.REDIS_DB_DATA_RECORD_RECOPY, JSON.stringify(row));
    router.push({
      name: 'RedisDBDataCopy',
    });
  };

  const handleClickRelatedTicket = (billId: number) => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        filterId: billId,
      },
    });
    window.open(route.href);
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
    color: #63656E;
    text-align: center;
    background: #F0F1F5;
    border-radius: 2px;
  }
}

.normal-color {
  td {
    .cell {
      color: #63656E !important;
    }
  }
}

.disable-color {
  td {
    .cell {
      color: #C4C6CC !important;
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

.recopy-dialog {
  :deep(.bk-modal-content) {
    padding: 0 43px 24px;
  }

  :deep(.bk-dialog-header) {
    padding: 48px 24px 18px;
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
