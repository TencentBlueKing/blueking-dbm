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
  <div class="bigdata-instance-detail">
    <BkCollapse
      v-model="activeIndex"
      header-icon="right-shape">
      <BkCollapsePanel name="baseInfo">
        <span class="panel-title">{{ t('基本信息') }}</span>
        <template #content>
          <EditInfo
            :columns="infoColumns"
            :data="data" />
        </template>
      </BkCollapsePanel>
      <BkCollapsePanel
        class="instance-list-penel mt-8"
        name="instanceList">
        <span class="panel-title">{{ t('实例列表') }}</span>
        <template #content>
          <div class="mb-12">
            <BkButton
              :disabled="isBatchRestartDisabled || isRestartActionDisabled"
              :loading="isBatchRestartLoading"
              @click="handleRestart()">
              {{ t('批量重启') }}
            </BkButton>
          </div>
          <BkLoading
            :loading="isLoading"
            :z-index="2">
            <DbOriginalTable
              :columns="tableColumns"
              :data="tableData"
              :is-anomalies="isAnomalies" />
          </BkLoading>
        </template>
      </BkCollapsePanel>
    </BkCollapse>
  </div>
</template>

<script
  setup
  lang="tsx"
  generic="T extends EsNodeModel | HdfsNodeModel | KafkaNodeModel | PulsarNodeModel | DorisNodeModel">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import type DorisInstanceModel from '@services/model/doris/doris-instance';
  import type DorisNodeModel from '@services/model/doris/doris-node';
  import type EsInstanceModel from '@services/model/es/es-instance';
  import type EsNodeModel from '@services/model/es/es-node';
  import type HdfsInstanceModel from '@services/model/hdfs/hdfs-instance';
  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import type KafkaInstanceModel from '@services/model/kafka/kafka-instance';
  import type KafkaNodeModel from '@services/model/kafka/kafka-node';
  import type PulsarInstanceModel from '@services/model/pulsar/pulsar-instance';
  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';
  import { getDorisInstanceList } from '@services/source/doris';
  import { getEsInstanceList } from '@services/source/es';
  import { getHdfsInstanceList } from '@services/source/hdfs';
  import { getKafkaInstanceList } from '@services/source/kafka';
  import { getPulsarInstanceList } from '@services/source/pulsar';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderInstanceStatus from '@components/cluster-common/RenderInstanceStatus.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTagNew.vue';
  import EditInfo, { type InfoColumn } from '@components/editable-info/index.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';

  import { useTimeoutPoll } from '@vueuse/core';

  type InstanceModel = EsInstanceModel | HdfsInstanceModel | KafkaInstanceModel | PulsarInstanceModel | DorisInstanceModel

  interface Props {
    clusterId: number,
    clusterType: 'es' | 'hdfs' | 'kafka' | 'pulsar' | 'doris'
    data: T,
  }

  interface Emits {
    (e: 'close'): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const activeIndex = ref(['baseInfo', 'instanceList']);
  const isAnomalies = ref(false);
  const isLoading = ref(true);
  const isBatchRestartLoading = ref(false);
  const isRestartLoading = ref(false);
  const isRestartActionDisabled = ref(false);
  const isSelectedAll = ref(false);

  const tableData = shallowRef<Array<InstanceModel>>([]);
  const batchSelectNodeMap = shallowRef<Record<number, InstanceModel>>({});

  const isBatchRestartDisabled = computed(() => Object.keys(batchSelectNodeMap.value).length === 0);
  const isIndeterminate = computed(() => !isSelectedAll.value && Object.keys(batchSelectNodeMap.value).length > 0);
  const mainSelectDisable = computed(() => tableData.value.every(tableItem => tableItem.operationRunningStatus));

  const infoColumns: InfoColumn[][] = [
    [
      {
        label: t('节点IP'),
        key: 'ip',
      },
      {
        label: t('主机名称'),
        key: 'bk_host_name',
      },
      {
        label: t('Agent状态'),
        key: 'status',
        render: () => <RenderHostStatus data={props.data.status} />
      },
    ],
    [
      {
        label: t('类型'),
        key: 'roleLabel',
      },
      {
        label: t('实例数量'),
        key: 'node_num',
      },
      {
        label: t('内存'),
        key: 'memText',
      },
    ],
  ]

  const tableColumns = [
    {
      width: 60,
      label: () => (
        <bk-checkbox
          model-value={isSelectedAll.value}
          indeterminate={isIndeterminate.value}
          disabled={mainSelectDisable.value}
          label={true}
          onChange={handleSelectAll}
        />
      ),
      render: ({ data }: { data: InstanceModel }) => (
        <bk-popover
          theme="dark"
          placement="top">
          {{
            default: () => (
              <bk-checkbox
                style="vertical-align: middle;"
                model-value={Boolean(batchSelectNodeMap.value[data.id])}
                label={true}
                disabled={Boolean(data.operationRunningStatus)}
                onChange={(value: boolean) => handleSelectRow(data, value)}
              />
            ),
            content: () => <span>{t('实例正在重启中，不能勾选')}</span>,
          }}
        </bk-popover>
      )
    },
    {
      label: t('实例'),
      field: 'instance_address',
      render: ({ data }: { data: InstanceModel }) => (
        <div>
          <span>{data.instance_address || '--'}</span>
          {
            data.operationTagTips.map(item => <RenderOperationTag class="ml-4" data={item}/>)
          }
        </div>
      ),
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data }: { data: InstanceModel }) => (
        <>
          {
            data.operationRunningStatus
            ? (
              <div class='loading-box'>
                <db-icon
                  class="rotate-loading mr-4"
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
      render: ({ data }: { data: InstanceModel }) => data.restart_at || '--',
    },
    {
      label: t('操作'),
      width: 116,
      render: ({ data }: { data: InstanceModel }) => (
        <OperationBtnStatusTips data={data}>
          <bk-button
            theme="primary"
            text
            disabled={data.operationDisabled || isRestartActionDisabled.value}
            onClick={() => handleRestart(data)}>
            { t('重启') }
          </bk-button>
        </OperationBtnStatusTips>
      ),
    },
  ];

  const fetchData = () => {
    isLoading.value = true;
    const apiMap = {
      es: getEsInstanceList,
      hdfs: getHdfsInstanceList,
      kafka: getKafkaInstanceList,
      pulsar: getPulsarInstanceList,
      doris: getDorisInstanceList,
    }
    apiMap[props.clusterType]({
      bk_biz_id: currentBizId,
      cluster_id: props.clusterId,
      ip: props.data.ip,
    })
      .then((data) => {
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

  watch(() => props.data, () => {
    isSelectedAll.value = false
    batchSelectNodeMap.value = {}
  })

  // 选择单台
  const handleSelectRow = (data: InstanceModel, value: boolean) => {
    const selectNodeMap = { ...batchSelectNodeMap.value };
    if (value) {
      selectNodeMap[data.id] = data;
    } else {
      delete selectNodeMap[data.id];
    }

    batchSelectNodeMap.value = selectNodeMap;

    if (Object.keys(selectNodeMap).length === tableData.value.filter(tableItem => !tableItem.operationRunningStatus).length) {
      isSelectedAll.value = true
    } else {
      isSelectedAll.value = false
    }
  };

  // 选择所有
  const handleSelectAll = (value: boolean) => {
    let selectNodeMap = batchSelectNodeMap.value;
    if (value) {
      selectNodeMap = tableData.value.reduce((result, item) => {
        if (item.operationRunningStatus) {
          return result
        }
        return {
          ...result,
          [item.id]: item,
        }
      }, {});
    } else {
      selectNodeMap = {};
    }
    batchSelectNodeMap.value = selectNodeMap;
    isSelectedAll.value = value
  };

  const formatRequestData = (data: Array<InstanceModel>) => data.map((item) => {
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

  const handleRestart = (data?: InstanceModel) => {
    if (data) {
      isRestartLoading.value = true;
    } else {
      isBatchRestartLoading.value = true;
    }

    const instanceList = data ? [data] : Object.values(batchSelectNodeMap.value)
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div class='tips-item'>
          {t('实例')} :
          <span
            style="color: #313238"
            class="ml-8">
            {instanceList.map(instanceItem => instanceItem.instance_address)}
          </span>
        </div>
        <div class='mt-4'>{t('连接将会断开，请谨慎操作！')}</div>
      </div>
    )

    InfoBox({
      title: t('确认重启该实例？'),
      subTitle,
      infoType: 'warning',
      confirmText: t('确认重启'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      extCls: 'bigdata-replace-model',
      onClose: () => {
        if (data) {
          isRestartLoading.value = false;
        } else {
          isBatchRestartLoading.value = false;
        }
      },
      onConfirm: () => {
        isRestartActionDisabled.value = true;
        const clusterTypeMap = {
          es: TicketTypes.ES_REBOOT,
          hdfs: TicketTypes.HDFS_REBOOT,
          kafka: TicketTypes.KAFKA_REBOOT,
          pulsar: TicketTypes.PULSAR_REBOOT,
          doris: TicketTypes.DORIS_REBOOT,
        }
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: clusterTypeMap[props.clusterType],
          details: {
            cluster_id: props.clusterId,
            instance_list: formatRequestData(instanceList),
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
            if (data) {
              isRestartLoading.value = false;
            } else {
              isBatchRestartLoading.value = false;
            }
          });
      },
    });
  };
</script>

<style lang="less">
  .bigdata-replace-model {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
<style lang="less" scoped>
  .bigdata-instance-detail {
    padding: 20px 24px;

    .panel-title {
      font-weight: 700;
      color: #313238;
    }

    .instance-list-penel {
      :deep(.bk-collapse-content) {
        padding: 5px 16px;
      }
    }

    :deep(.loading-box) {
      display: flex;
      align-items: center;
    }
  }
</style>
