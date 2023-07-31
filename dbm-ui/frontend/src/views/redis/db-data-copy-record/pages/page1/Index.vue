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
  <SmartAction :show-action-area="false">
    <BkInput
      v-model="searchValue"
      clearable
      :placeholder="$t('请输入集群名称')"
      style="width:500px;margin-bottom: 16px;"
      type="search"
      @enter="handleClickSearch" />
    <div class="redis-struct-ins-page">
      <BkLoading
        :loading="isTableDataLoading"
        :z-index="2">
        <DbOriginalTable
          :columns="columns"
          :data="tableData"
          :settings="settings" />
      </BkLoading>
    </div>
    <DataCopyTransferDetail
      :data="currentActiveRow"
      :is-show="isShowDataCopyTransferDetail"
      @on-close="() => isShowDataCopyTransferDetail = false" />
    <BkDialog
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
    </BkDialog>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisDSTHistoryJobModel, { CopyModes } from '@services/model/redis/redis-dst-history-job';
  import { getRedisDTSHistoryJobs } from '@services/redis/toolbox';

  import { LocalStorageKeys, TicketTypes  } from '@common/const';

  // import { createTicket } from '@services/ticket';
  // import type { SubmitTicket } from '@services/types/ticket';
  // import { useGlobalBizs } from '@stores';
  // import { TicketTypes  } from '@common/const';
  import DataCopyTransferDetail from './DataCopyTransferDetail.vue';
  import ExecuteStatus, { TransmissionTypes } from './ExecuteStatus.vue';


  // interface InfoItem {
  //   related_rollback_bill_id: number,
  //   prod_cluster: string,
  //   bk_cloud_id: number,
  // }


  // const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  const tableData = ref<RedisDSTHistoryJobModel[]>([]);
  const isTableDataLoading = ref(false);
  const isShowDataCopyTransferDetail = ref(false);
  const currentActiveRow = ref<RedisDSTHistoryJobModel>();
  const copyType = ref(0);
  const showRecopyDialog = ref(false);
  const searchValue = ref('');
  const timer = ref();

  const settings = {
    checked: ['src_cluster', 'dst_cluster', 'copy_type', 'key_white_regex', 'key_black_regex', 'relate_ticket', 'latest_modify', 'status', 'create_time'],
  };


  const copyTypesMap = {
    [CopyModes.CROSS_BISNESS]: t('跨业务'),
    [CopyModes.INTRA_BISNESS]: t('业务内'),
    [CopyModes.INTRA_TO_THIRD]: t('业务内至第三方'),
    [CopyModes.SELFBUILT_TO_INTRA]: t('自建集群至业务内'),
  };

  // 渲染操作区按钮
  const renderOperation = (data: RedisDSTHistoryJobModel, index: number) => {
    const showDisconnect = false;
    const showDataCheckAndRepair = true;
    const showRecopy = false;
    // switch (data.status) {
    // case TransmissionTypes.FULL_TRANSFERING: // 全量传输中
    //   showDisconnect = true;
    //   break;
    // case TransmissionTypes.INCREMENTAL_TRANSFERING: // 增量传输中
    //   showDisconnect = true;
    //   showDataCheckAndRepair = true;
    //   break;
    // case TransmissionTypes.FULL_TRANSFER_FAILED: // 全量传输失败
    //   break;
    // case TransmissionTypes.INCREMENTAL_TRANSFER_FAILED: // 增量传输失败
    //   showDisconnect = true;
    //   break;
    // case TransmissionTypes.TO_BE_EXECUTED: // 待执行
    //   break;
    // case TransmissionTypes.END_OF_TRANSMISSION: // 传输结束
    //   break;
    // case TransmissionTypes.TRANSSION_TERMINATE: // 传输终止
    //   showRecopy = true;
    //   break;
    // default:
    //   break;
    // }
    // “数据校验修复”只在状态为”增量传输中“ 可用，其他的不可用
    // "构造实例到业务" 内 不做 数据校验，其他的都可以 发起 "数据校验修复"
    return (<div style="color:#3A84FF;cursor:pointer;'">
        {showRecopy
          ? <span onClick={() => handleClickRecopy(data, index)}>{t('重新复制')}</span>
          : <>
          <span style={{ color: showDisconnect ? '#3A84FF' : '#C4C6CC' }} onClick={() => handleClickDisconnectSync(data, index, showDisconnect)}>{t('断开同步')}</span>
          <span style={{ color: showDataCheckAndRepair ? '#3A84FF' : '#C4C6CC', marginLeft: '10px' }} onClick={() => handleClickDataCheckAndRepair(data, index, showDataCheckAndRepair)}>{t('数据校验与修复')}</span>
          </>
        }
      </div>);
  };

  const columns = [
    {
      label: t('源集群'),
      field: 'src_cluster',
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span style="color:#3A84FF;cursor:pointer;" onClick={() => handleClickOpenTransferDetail(data)}>{data.src_cluster}</span>,
    },
    {
      minWidth: 100,
      label: t('目标集群'),
      field: 'dst_cluster',
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
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span>{copyTypesMap[data.dts_copy_type]}</span>,
    },
    {
      label: t('包含 key'),
      field: '',
      showOverflowTooltip: true,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <bk-tag type="stroke">无</bk-tag>,
    },
    {
      label: t('排除 key'),
      field: 'key_black_regex',
      showOverflowTooltip: true,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span>--</span>
      // if (data.key_black_regex) {
      //   if (data.key_black_regex.includes('\n')) {
      //     const tags = data.key_black_regex.split('\n');
      //     return tags.map(tag => <bk-tag type="stroke">{tag}</bk-tag>);
      //   }
      //   return <bk-tag type="stroke">{data.key_black_regex}</bk-tag>;
      // }

      ,
    },
    {
      label: t('关联单据'),
      field: 'bill_id',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: RedisDSTHistoryJobModel}) => <span style="color:#3A84FF;cursor:pointer;">{data.bill_id}</span>,
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
      field: '',
      showOverflowTooltip: true,
      width: 180,
      render: ({ index, data }: {index: number, data: RedisDSTHistoryJobModel}) => renderOperation(data, index),
    },
  ];

  const copyTypeList = [
    {
      label: t('全量覆盖同名 Key（如：del  $key+ hset $key）'),
      value: 0,
    },
    {
      label: t('增量覆盖同名 Key（如：hset $key）'),
      value: 1,
    },
    {
      label: t('清空目标集群所有数据'),
      value: 2,
    },
  ];

  const tableRawData = tableData.value;

  watch(searchValue, (str) => {
    if (str) {
      clearTimeout(timer.value);
      timer.value = setTimeout(() => {
        tableData.value = tableRawData.filter(item => item.src_cluster.includes(str) || item.dst_cluster.includes(str));
      }, 1000);
    } else {
      tableData.value = tableRawData;
    }
  });

  const handleClickSearch = (value: string) => {
    console.log('search: ', value);
  };

  const queryRecords = async () => {
    const ret = await getRedisDTSHistoryJobs({
      start_time: dayjs(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)).format('YYYY-MM-DD HH:mm:ss'),
      end_time: dayjs(new Date()).format('YYYY-MM-DD HH:mm:ss'),
    });
    tableData.value = ret.jobs;
  };

  queryRecords();

  const handleClickOpenTransferDetail = (row: RedisDSTHistoryJobModel) => {
    currentActiveRow.value = row;
    isShowDataCopyTransferDetail.value = true;
  };

  const handleClickDisconnectSync = (row: RedisDSTHistoryJobModel, index: number, isAvailable: boolean) => {
    if (isAvailable) {
      InfoBox({
        title: t('确认断开同步？'),
        subTitle: t('断开后，数据将不会再再自动同步，请谨慎操作！'),
        width: 420,
        infoType: 'warning',
        confirmText: '断开同步',
        onConfirm: () => {
          // if (row.status === TransmissionTypes.INCREMENTAL_TRANSFERING) {
          //   tableData.value[index].status = TransmissionTypes.END_OF_TRANSMISSION;
          // } else {
          //   tableData.value[index].status = TransmissionTypes.TRANSSION_TERMINATE;
          // }
        } });
    }
  };

  const handleClickDataCheckAndRepair = (row: RedisDSTHistoryJobModel, index: number, isAvailable: boolean) => {
    if (!isAvailable) {
      return;
    }
    localStorage.setItem(LocalStorageKeys.DATA_CHECK_AND_REPAIR, JSON.stringify(row));
    router.push({
      name: 'RedisToolboxDataCheckRepair',
    });
  };


  const handleClickRecopy = (row: RedisDSTHistoryJobModel, index: number) => {
    currentActiveRow.value = row;
    showRecopyDialog.value = true;
  };

  const handleClickConfirmRecopy = () => {
    console.log(currentActiveRow.value);
  };

  const handleClickCancelRecopy = () => {
    showRecopyDialog.value = false;
  };


</script>

<style lang="less" scoped>

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

.first-column {
  display: flex;
  align-items: center;

  .tag-tip {
    padding: 1px 4px;
    font-weight: 700;
    transform : scale(0.83,0.83);
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
