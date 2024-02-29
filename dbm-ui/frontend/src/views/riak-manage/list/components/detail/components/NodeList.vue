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
  <div class="riak-detail-node-list">
    <div class="action-box">
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleAddNode">
        {{ t('添加节点') }}
      </BkButton>
      <BkButton
        class="mr-8"
        @click="handleDeleteNode">
        {{ t('删除节点') }}
      </BkButton>
      <BkDropdown
        class="mr-8"
        @hide="() => (isCopyDropdown = false)"
        @show="() => (isCopyDropdown = true)">
        <BkButton>
          {{ t('复制IP') }}
          <DbIcon
            class="action-copy-icon"
            :class="{
              'action-copy-icon--avtive': isCopyDropdown,
            }"
            type="up-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopyAll">
              {{ t('复制全部IP') }}
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                v-bk-tooltips="{
                  content: t('暂无异常IP'),
                  disabled: isAbnormalNodeExits,
                }"
                :disabled="!isAbnormalNodeExits"
                text
                @click="handleCopyAbmormal">
                {{ t('复制异常IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                v-bk-tooltips="{
                  content: t('请先勾选IP'),
                  disabled: isTableSelected,
                }"
                :disabled="!isTableSelected"
                text
                @click="handleCopySelected">
                {{ t('复制已选IP') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkInput
        v-model="searchKey"
        class="action-box-search"
        clearable
        :placeholder="t('请输入节点实例或选择字段搜索')"
        @change="() => fetchData()" />
    </div>
    <BkAlert
      v-if="operationData?.operationStatusText"
      class="mb16"
      theme="warning">
      <I18nT
        keypath="当前集群有xx暂时不能进行其他操作跳转xx查看进度"
        tag="div">
        <span>{{ operationData?.operationStatusText }}</span>
        <RouterLink
          target="_blank"
          :to="{
            name: 'SelfServiceMyTickets',
            query: {
              id: operationData?.operationTicketId,
            },
          }">
          {{ t('我的服务单') }}
        </RouterLink>
      </I18nT>
    </BkAlert>
    <DbTable
      ref="tableRef"
      class="node-list-table"
      :columns="columns"
      :data-source="getRiakNodeList"
      primary-key="bk_host_id"
      :row-class="setRowClass"
      selectable
      @column-filter="handleColunmFilter"
      @colunm-sort="fetchData"
      @selection="handleSelection" />
    <DbSideslider
      v-model:is-show="addNodeShow"
      quick-close
      :title="t('添加节点【xx】', [data.cluster_name])"
      :width="960">
      <AddNodes
        :data="data"
        @submit-success="fetchData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="deleteNodeShow"
      :title="t('删除节点【xx】', [data.cluster_name])"
      :width="960">
      <DeleteNodes
        :data="data"
        @submit-success="fetchData" />
    </DbSideslider>
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RiakModel from '@services/model/riak/riak';
  import RiakNodeModel from '@services/model/riak/riak-node';
  import {
    getRiakDetail,
    getRiakNodeList,
  } from '@services/source/riak';
  import { createTicket } from '@services/source/ticket';

  import {
    useCopy,
    useDebouncedRef,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import DbTable from '@components/db-table/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import RenderHostStatus from '@components/render-host-status/Index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import { messageWarn } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import AddNodes from '../../components/AddNodes.vue';
  import DeleteNodes from '../../components/DeleteNodes.vue';

  interface Props {
    data: RiakModel
  }

  const props = defineProps<Props>();

  const copy = useCopy();
  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const searchKey = useDebouncedRef('');

  const { run: getRiakDetailRun } = useRequest(getRiakDetail, {
    manual: true,
    onSuccess(riakDetail) {
      operationData.value = riakDetail;
    },
  });

  const {
    pause: pauseFetchClusterDetail,
    resume: resumeFetchClusterDetail,
  } = useTimeoutPoll(() => getRiakDetailRun({ id: props.data.id }), 2000, {
    immediate: true,
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isCopyDropdown = ref(false);
  const addNodeShow = ref(false);
  const deleteNodeShow = ref(false);
  const selected = shallowRef<RiakNodeModel[]>([]);
  const operationData = shallowRef<RiakModel>();

  const setRowClass = (data: RiakNodeModel) => (data.isNewRow ? 'is-new-row' : '');

  const columns = [
    {
      label: t('节点实例'),
      field: 'ip',
      minWidth: 200,
      showOverflowTooltip: false,
      render: ({ row }: { row: RiakNodeModel }) => {
        const content = <>
          {
            row.isNewRow && (
              <MiniTag
                content='NEW'
                theme='success'>
              </MiniTag>
            )
          }
          <bk-button
            text
            theme="primary"
            onClick={(event: Event) => handleCopyRowIp(event, row.ip)}
          >
           <db-icon type="copy" />
          </bk-button>
        </>;

        return (
          <RenderTextEllipsisOneLine
            text={ row.ip }
            textStyle={{
              color: '#63656E',
              cursor: 'unset',
            }}>
            { content }
          </RenderTextEllipsisOneLine>
        );
      },
    },
    {
      label: t('Agent状态'),
      width: 100,
      render: ({ row }: { row: RiakNodeModel }) => (
        <RenderHostStatus data={row.status} />
      ),
    },
    // {
    //   label: t('CPU使用率'),
    //   width: 150,
    //   field: 'create_at',
    //   sort: true,
    //   render: ({ row }: { row: RiakNodeModel }) => {
    //     const cpuInfo = row.getCpuInfo;
    //     return (
    //       <div class='cpu-use-rate'>
    //         <bk-progress
    //           show-text={false}
    //           type="circle"
    //           width={24}
    //           stroke-linecap='square'
    //           percent={cpuInfo.percent}
    //           stroke-width={16}
    //           bg-color='#EAEBF0'
    //           color={cpuInfo.color}/>
    //         <span class='ml-8'>
    //           <span class='cpu-rate'>{cpuInfo.rate}</span>
    //           <span class='cpu-num'>{cpuInfo.num}</span>
    //         </span>
    //       </div>
    //     );
    //   },
    // },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      render: ({ row }: { row: RiakNodeModel }) => <span>{row.bk_cloud_name || '--'}</span>,
    },
    {
      label: t('机型'),
      field: 'bk_host_name',
      render: ({ row }: { row: RiakNodeModel }) => <span>{row.bk_host_name || '--'}</span>,
    },
    {
      label: t('部署时间'),
      width: 160,
      field: 'create_at',
      render: ({ row }: { row: RiakNodeModel }) => <span>{row.createAtDisplay || '--'}</span>,
    },
    {
      label: t('操作'),
      width: 120,
      fixed: 'right',
      render: ({ row }: { row: RiakNodeModel }) => (
        <>
          <OperationBtnStatusTips data={operationData.value}>
            <bk-button
              class="ml8"
              theme="primary"
              text
              disabled={operationData.value?.operationDisabled || dataList.value.length <= 3}
              onClick={() => handleDelete(row)}>
              { t('删除') }
            </bk-button>
          </OperationBtnStatusTips>
          <OperationBtnStatusTips data={operationData.value}>
            <bk-button
              theme="primary"
              text
              class="ml8"
              disabled={operationData.value?.operationDisabled}
              onClick={() => handleReboot(row)}>
              { t('重启') }
            </bk-button>
          </OperationBtnStatusTips>
        </>
      ),
    },
  ];

  const dataList = computed(() => tableRef.value!.getData<RiakNodeModel>());
  const isAbnormalNodeExits = computed(() => dataList.value
    .some((riakNode: RiakNodeModel) => !riakNode.isNodeNormal));
  const isTableSelected = computed(() => selected.value.length > 0);

  watch(() => props.data.id, () => {
    nextTick(() => {
      pauseFetchClusterDetail();
      resumeFetchClusterDetail();
      fetchData();
    });
  }, {
    immediate: true,
  });

  const handleSelection = (key: number[], list: Record<any, any>[]) => {
    selected.value = list as RiakNodeModel[];
  };

  const handleAddNode = () => {
    addNodeShow.value = true;
  };

  const handleDeleteNode = () => {
    deleteNodeShow.value = true;
  };

  const handleDelete = (row: RiakNodeModel) => {
    InfoBox({
      title: t('确认删除n个节点?', [1]),
      subTitle: (
        <>
          <p>{ t('节点IP') }：<span class='info-box-cluster-name'>{ row.ip }</span></p>
          <p class='mt-16'>{ t('删除后不可恢复，请谨慎操作!') }</p>
        </>
      ),
      confirmText: t('确定'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_SCALE_IN,
          details: {
            cluster_id: props.data.id,
            bk_cloud_id: row.bk_cloud_id,
            nodes: [{
              ip: row.ip,
              bk_host_id: row.bk_host_id,
              bk_cloud_id: row.bk_cloud_id,
              bk_biz_id: currentBizId,
            }],
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          })
        ;
      },
    });
  };

  const handleReboot = (row: RiakNodeModel) => {
    InfoBox({
      title: t('确认重启该节点?'),
      subTitle: (
        <p>{ t('节点IP') }：<span class='info-box-cluster-name'>{ row.ip }</span></p>
      ),
      confirmText: t('确定'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_REBOOT,
          details: {
            bk_host_id: row.bk_host_id,
            cluster_id: props.data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          })
        ;
      },
    });
  };

  const handleCopyRowIp = (event: Event, ip: string) => {
    event.stopPropagation();
    copy(ip);
  };

  const handleCopy = (ipList: string[]) => {
    if (ipList.length < 1) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    copy(ipList.join('\n'));
  };

  // 复制所有 IP
  const handleCopyAll = () => {
    const ipList = tableRef.value!.getData<RiakNodeModel>().map((riakNodeItem: RiakNodeModel) => riakNodeItem.ip);
    handleCopy(ipList);
  };

  // 复制异常 IP
  const handleCopyAbmormal = () => {
    const ipList = tableRef.value!.getData<RiakNodeModel>()
      .reduce((ipArr: Array<string>, riakNodeItem: RiakNodeModel) => {
        if (!riakNodeItem.isNodeNormal) {
          return [...ipArr, riakNodeItem.ip];
        }
        return ipArr;
      }, [] as Array<string>);

    handleCopy(ipList);
  };

  // 复制已选 IP
  const handleCopySelected = () => {
    const ipList = selected.value.map((riakNodeItem: RiakNodeModel) => riakNodeItem.ip);
    handleCopy(ipList);
  };

  const fetchData = (otherParamas: object = {}) => {
    tableRef.value!.fetchData(
      {
        ...otherParamas,
        ip: searchKey.value,
      },
      {
        bk_biz_id: currentBizId,
        cluster_id: props.data.id,
      },
    );
  };

  const handleColunmFilter = ({ checked }: { checked: string[] }) => {
    fetchData({ status: checked.join(',') });
  };
</script>

<style>
  .info-box-cluster-name {
    color: #313238;
  }
</style>

<style lang="less" scoped>
  .riak-detail-node-list {
    padding: 24px 0;

    .action-box {
      display: flex;
      margin-bottom: 16px;

      .action-box-search {
        width: 360px;
        margin-left: auto;
      }
    }

    .action-copy-icon {
      margin-left: 6px;
      color: #979ba5;
      transform: rotateZ(180deg);
      transition: all 0.2s;

      &--avtive {
        transform: rotateZ(0);
      }
    }

    :deep(.node-list-table) {
      .is-new-row {
        td {
          background-color: #f3fcf5 !important;
        }
      }

      .status-label {
        width: 38px;
        height: 16px;
        margin-right: 4px;
        flex-shrink: 0;
      }

      tr .db-icon-copy {
        display: none;
      }

      tr:hover .db-icon-copy {
        display: inline-block;
      }

      .cpu-use-rate {
        display: flex;
        align-items: center;

        .cpu-rate {
          font-weight: 700;
        }

        .cpu-num {
          color: #979ba5;
        }
      }
    }
  }
</style>
