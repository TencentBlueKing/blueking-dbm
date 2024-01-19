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
  <div class="cluster-node-list-box">
    <div style="margin-bottom: 12px;">
      <BkButton
        :disabled="isBatchRestartDisabled || isRestartActionDisabled"
        :loading="isBatchRestartLoading"
        @click="handleBatchRestart">
        {{ $t('批量重启') }}
      </BkButton>
    </div>
    <BkLoading :loading="isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        @refresh="fetchData(true)"
        @select="handleSelect"
        @select-all="handleSelectAll" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import {
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type HdfsInstanceModel from '@services/model/hdfs/hdfs-instance';
  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import { getHdfsInstanceList } from '@services/source/hdfs';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderInstanceStatus from '@components/cluster-common/RenderInstanceStatus.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';

  import { useTimeoutPoll } from '@vueuse/core';

  interface Emits {
    (e: 'close'): void
  }

  interface Props {
    clusterId: number,
    data: HdfsNodeModel
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const formatRequestData = (data: Array<HdfsInstanceModel>) => data.map((item) => {
    const [ip, port] = item.instance_address.split(':');
    return ({
      ip,
      port: Number(port),
      instance_name: item.instance_name,
      bk_host_id: item.bk_host_id,
      bk_cloud_id: item.bk_cloud_id,
      instance_id: item.id,
    });
  });

  const isAnomalies = ref(false);
  const isLoading = ref(true);
  const isBatchRestartLoading = ref(false);
  const isRestartLoading = ref(false);
  const isRestartActionDisabled = ref(false);
  const tableData = shallowRef<Array<HdfsInstanceModel>>([]);
  const batchSelectNodeMap = shallowRef<Record<number, HdfsInstanceModel>>({});

  const globalBizsStore = useGlobalBizs();

  const isBatchRestartDisabled = computed(() => Object.keys(batchSelectNodeMap.value).length < 1);

  const columns = [
    {
      type: 'selection',
      width: 48,
      label: '',
      fixed: 'left',
    },
    {
      label: t('实例'),
      field: 'instance_address',
      render: ({ data }: {data:HdfsInstanceModel}) => (
        <div>
          <span>{data.instance_address || '--'}</span>
          <RenderOperationTag data={data} style='margin-left: 3px;' />
        </div>
      ),
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data }: {data: HdfsInstanceModel}) => (
        <>
          {data.operationRunningStatus
            ? (
              <div class='loading-box'>
                <db-icon
                  class="rotate-loading"
                  style="margin-right: 4px"
                  type='loading'
                  svg />
                <div>{ t('重启中') }</div>
              </div>
            )
            : <RenderInstanceStatus data={data.status} />
          }
        </>
      ),
    },
    {
      label: t('上次重启时间'),
      field: 'restart_at',
      render: ({ data }: {data:HdfsInstanceModel}) => data.restart_at || '--',
    },
    {
      label: t('操作'),
      width: 116,
      render: ({ data }: {data:HdfsInstanceModel}) => (
        <OperationBtnStatusTips data={data}>
          <bk-button
            theme="primary"
            text
            disabled={data.operationDisabled || isRestartActionDisabled.value}
            onClick={() => handleRestartOnde(data)}>
            { t('重启') }
          </bk-button>
        </OperationBtnStatusTips>
      ),
    },
  ];

  const fetchData = (hasLoading = false) => {
    isLoading.value = hasLoading;
    getHdfsInstanceList({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.clusterId,
      ip: props.data.ip,
    }).then((data) => {
      tableData.value = data.results;
      isAnomalies.value = false;
    })
      .catch(() => {
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  useTimeoutPoll(fetchData, 5000, {
    immediate: true,
  });

  // 选择单台
  const handleSelect = (data: { checked: boolean, row: HdfsInstanceModel }) => {
    const selectedMap = { ...batchSelectNodeMap.value };
    if (data.checked) {
      selectedMap[data.row.id] = data.row;
    } else {
      delete selectedMap[data.row.id];
    }

    batchSelectNodeMap.value = selectedMap;
  };

  // 选择所有
  const handleSelectAll = (data:{checked: boolean}) => {
    let selectedMap = { ...batchSelectNodeMap.value };
    if (data.checked) {
      selectedMap = tableData.value.reduce((result, item) => ({
        ...result,
        [item.id]: item,
      }), {});
    } else {
      selectedMap = {};
    }
    batchSelectNodeMap.value = selectedMap;
  };

  // 批量重试
  const handleBatchRestart = () => {
    isBatchRestartLoading.value = true;
    InfoBox({
      title: t('确认批量重启'),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onClosed: () => {
        isBatchRestartLoading.value = false;
      },
      onConfirm: () => {
        isRestartActionDisabled.value = true;
        createTicket({
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: 'HDFS_REBOOT',
          details: {
            cluster_id: props.clusterId,
            instance_list: formatRequestData(Object.values(batchSelectNodeMap.value)),
          },
        })
          .then((data) => {
            ticketMessage(data.id);
            fetchData();
            window.changeConfirm = false;
            emits('close');
          })
          .finally(() => {
            isRestartActionDisabled.value = false;
            isBatchRestartLoading.value = false;
          });
      },
    });
  };

  // 重试单台
  const handleRestartOnde = (data: HdfsInstanceModel) => {
    isRestartLoading.value = true;
    InfoBox({
      title: t('确认重启xx', { name: data.instance_address }),
      subTitle: '',
      confirmText: t('确认'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onClosed: () => {
        isRestartLoading.value = false;
      },
      onConfirm: () => {
        isRestartActionDisabled.value = true;
        createTicket({
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: 'HDFS_REBOOT',
          details: {
            cluster_id: props.clusterId,
            instance_list: formatRequestData([data]),
          },
        })
          .then((data) => {
            ticketMessage(data.id);
            fetchData();
            window.changeConfirm = false;
            emits('close');
          })
          .finally(() => {
            isRestartActionDisabled.value = false;
            isRestartLoading.value = false;
          });
      },
    });
  };
</script>
<style lang="less">
  .cluster-node-list-box {
    padding: 28px 40px;

    .loading-box {
      display: flex;
      align-items: center;
    }
  }
</style>
