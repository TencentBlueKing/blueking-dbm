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
      type="search" />
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

<script lang="tsx">
  import { CopyModes } from '@views/redis/db-data-copy/pages/page1/Index.vue';
  export interface DataRow {
    src_cluster: string,
    dst_cluster: string,
    copy_type: CopyModes,
    key_white_regex: string,
    key_black_regex: string,
    relate_ticket: number,
    latest_modify: number,
    status: TransmissionTypes,
    create_time: string,
  }
</script>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  // import { useRouter } from 'vue-router';
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
  // const router = useRouter();

  const tableData = ref<DataRow[]>([
    {
      src_cluster: 'adfwrgrgcdc',
      dst_cluster: 'sgeththeth',
      copy_type: CopyModes.INTRA_BISNESS,
      key_white_regex: '*',
      key_black_regex: '6666\n7777',
      relate_ticket: 2323,
      latest_modify: 2323,
      status: TransmissionTypes.FULL_TRANSFERING,
      create_time: '2023-12-20 12:00:00',
    },
    {
      src_cluster: 'adfwrgrgcdc',
      dst_cluster: 'sgeththeth',
      copy_type: CopyModes.CROSS_BISNESS,
      key_white_regex: '*',
      key_black_regex: '6666\n7777',
      relate_ticket: 2323,
      latest_modify: 2323,
      status: TransmissionTypes.FULL_TRANSFER_FAILED,
      create_time: '2023-12-20 12:00:00',
    },
    {
      src_cluster: 'adfwrgrgcdc',
      dst_cluster: 'sgeththeth',
      copy_type: CopyModes.INTRA_TO_THIRD,
      key_white_regex: '*',
      key_black_regex: '',
      relate_ticket: 2323,
      latest_modify: 2323,
      status: TransmissionTypes.END_OF_TRANSMISSION,
      create_time: '2023-12-20 12:00:00',
    },
    {
      src_cluster: 'adfwrgrgcdc',
      dst_cluster: 'sgeththeth',
      copy_type: CopyModes.SELFBUILT_TO_INTRA,
      key_white_regex: '*',
      key_black_regex: '6666\n7777',
      relate_ticket: 2323,
      latest_modify: 2323,
      status: TransmissionTypes.INCREMENTAL_TRANSFERING,
      create_time: '2023-12-20 12:00:00',
    },
  ]);
  const isTableDataLoading = ref(false);
  const isShowDataCopyTransferDetail = ref(false);
  const currentActiveRow = ref<DataRow>();
  const copyType = ref(0);
  const showRecopyDialog = ref(false);
  const searchValue = ref('');
  const timer = ref();

  const settings = {
    checked: ['src_cluster', 'dst_cluster', 'copy_type', 'key_white_regex', 'key_black_regex', 'relate_ticket', 'latest_modify', 'status', 'create_time'],
  };

  // 渲染操作区按钮
  const renderOperation = (data: DataRow, index: number) => {
    let showDisconnect = false;
    let showDataCheckAndRepair = false;
    let showRecopy = false;
    switch (data.status) {
    case TransmissionTypes.FULL_TRANSFERING: // 全量传输中
      showDisconnect = true;
      break;
    case TransmissionTypes.INCREMENTAL_TRANSFERING: // 增量传输中
      showDisconnect = true;
      showDataCheckAndRepair = true;
      break;
    case TransmissionTypes.FULL_TRANSFER_FAILED: // 全量传输失败
      break;
    case TransmissionTypes.INCREMENTAL_TRANSFER_FAILED: // 增量传输失败
      showDisconnect = true;
      showDataCheckAndRepair = true;
      break;
    case TransmissionTypes.TO_BE_EXECUTED: // 待执行
      break;
    case TransmissionTypes.END_OF_TRANSMISSION: // 传输结束
      showDataCheckAndRepair = true;
      break;
    case TransmissionTypes.TRANSSION_TERMINATE: // 传输终止
      showRecopy = true;
      break;
    default:
      break;
    }
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
      render: ({ data }: {data: DataRow}) => <span style="color:#3A84FF;cursor:pointer;" onClick={() => handleClickOpenTransferDetail(data)}>{data.src_cluster}</span>,
    },
    {
      minWidth: 100,
      label: t('目标集群'),
      field: 'dst_cluster',
    },
    {
      label: t('复制类型'),
      filter: {
        list: [{ text: 'master', value: 'master' }, { text: 'slave', value: 'slave' }, { text: 'proxy', value: 'proxy' }],
      },
      field: 'copy_type',
    },
    {
      label: t('包含 key'),
      field: 'key_white_regex',
      showOverflowTooltip: true,
      render: ({ data }: {data: DataRow}) => <bk-tag type="stroke">{data.key_white_regex}</bk-tag>,
    },
    {
      label: t('排除 key'),
      field: 'key_black_regex',
      showOverflowTooltip: true,
      render: ({ data }: {data: DataRow}) => {
        if (data.key_black_regex) {
          if (data.key_black_regex.includes('\n')) {
            const tags = data.key_black_regex.split('\n');
            return tags.map(tag => <bk-tag type="stroke">{tag}</bk-tag>);
          }
          return <bk-tag type="stroke">{data.key_black_regex}</bk-tag>;
        }
        return <span>--</span>;
      },
    },
    {
      label: t('关联单据'),
      field: 'relate_ticket',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: DataRow}) => <span style="color:#3A84FF;cursor:pointer;">{data.relate_ticket}</span>,
    },
    {
      label: t('最近一次修复单'),
      field: 'latest_modify',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('状态'),
      field: 'status',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: DataRow}) => <ExecuteStatus type={data.status} />,
    },
    {
      label: t('创建时间'),
      field: 'create_time',
      showOverflowTooltip: true,
      width: 180,
    },
    {
      label: t('操作'),
      field: 'cluster',
      showOverflowTooltip: true,
      width: 180,
      render: ({ index, data }: {index: number, data: DataRow}) => renderOperation(data, index),
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

  const handleClickOpenTransferDetail = (row: DataRow) => {
    currentActiveRow.value = row;
    isShowDataCopyTransferDetail.value = true;
  };

  const handleClickDisconnectSync = (row: DataRow, index: number, isAvailable: boolean) => {
    if (isAvailable) {
      InfoBox({
        title: t('确认断开同步？'),
        subTitle: t('断开后，数据将不会再再自动同步，请谨慎操作！'),
        width: 420,
        infoType: 'warning',
        confirmText: '断开同步',
        onConfirm: () => {
          if (row.status === TransmissionTypes.INCREMENTAL_TRANSFERING) {
            tableData.value[index].status = TransmissionTypes.END_OF_TRANSMISSION;
          } else {
            tableData.value[index].status = TransmissionTypes.TRANSSION_TERMINATE;
          }
        } });
    }
  };

  const handleClickDataCheckAndRepair = (row: DataRow, index: number, isAvailable: boolean) => {
    if (isAvailable) {
      currentActiveRow.value = row;
    }
  };


  const handleClickRecopy = (row: DataRow, index: number) => {
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
