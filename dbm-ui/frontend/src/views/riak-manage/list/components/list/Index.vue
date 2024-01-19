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
  <div class="riak-list-container">
    <div class="header-action">
      <BkButton
        theme="primary"
        @click="toApply">
        {{ t('申请实例') }}
      </BkButton>
      <DropdownExportExcel
        class="mr-8"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="riak" />
      <DbSearchSelect
        v-model="searchValues"
        class="header-action-search-select"
        :data="serachData"
        :placeholder="t('输入集群名_IP_访问入口关键字')"
        unique-select
        @change="() => fetchData()" />
      <BkDatePicker
        v-model="deployTime"
        append-to-body
        class="header-action-deploy-time"
        clearable
        :placeholder="t('请选择xx', [t('部署时间')])"
        type="daterange"
        @change="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      class="riak-list-table"
      :columns="columns"
      :data-source="getRiakList"
      :row-class="setRowClass"
      selectable
      @column-filter="handleColunmFilter"
      @colunm-sort="fetchData"
      @selection="handleSelection" />
    <DbSideslider
      v-if="detailData"
      v-model:is-show="addNodeShow"
      quick-close
      :title="t('添加节点【xx】', [detailData.cluster_name])"
      :width="960">
      <AddNodes
        :id="detailData.id"
        :cloud-id="detailData.bk_cloud_id"
        @submit-success="fetchData" />
    </DbSideslider>
    <DbSideslider
      v-if="detailData"
      v-model:is-show="deleteNodeShow"
      :title="t('删除节点【xx】', [detailData.cluster_name])"
      :width="960">
      <DeleteNodes
        :id="detailData.id"
        :cloud-id="detailData.bk_cloud_id"
        @submit-success="fetchData" />
    </DbSideslider>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RiakModel from '@services/model/riak/riak';
  import {
    getRiakInstanceList,
    getRiakList,
  } from '@services/source/riak';
  import { createTicket } from '@services/source/ticket';

  import {
    useStretchLayout,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderNodeInstance from '@components/cluster-common/RenderNodeInstance.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import DbTable from '@components/db-table/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import AddNodes from '../components/AddNodes.vue';
  import DeleteNodes from '../components/DeleteNodes.vue';

  interface Emits {
    (e: 'detailOpenChange', data: boolean): void
  }

  interface Expose {
    freshData: () => void
  }

  const emits = defineEmits<Emits>();
  const clusterId = defineModel<number>('clusterId');

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const ticketMessage = useTicketMessage();

  const columns = [
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 240,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: { data: RiakModel }) => {
        const content = <>
          {
            data.isNewRow && (
             <MiniTag
                content='NEW'
                theme='success'
                class='new-tag'>
              </MiniTag>
            )
          }
          {
            data.operations.map(item => (
              <RenderOperationTag
                iconMap={RiakModel.operationIconMap}
                tipMap={RiakModel.operationTextMap}
                class="ml-4" data={item}/>
            ))
          }
          {
            data.isDisabled && (
              <db-icon
                svg
                type="yijinyong"
                class="disabled-tag" />
            )
          }
        </>;

        return (
        <>
          <RenderTextEllipsisOneLine
            text={data.cluster_name}
            textStyle={{
              fontWeight: '700',
            }}
            onClick={() => toDetail(data.id)}>
            {content}
          </RenderTextEllipsisOneLine>
          <span style='color: #C4C6CC;'>{data.cluster_alias || '--'}</span>
        </>
        );
      },
    },
    {
      label: t('版本'),
      field: 'major_version',
      width: 80,
      sort: true,
      render: ({ data }: { data: RiakModel }) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('管控区域'),
      width: 120,
      field: 'bk_cloud_name',
      render: ({ data }: { data: RiakModel }) => <span>{data.bk_cloud_name || '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      sort: true,
      width: 100,
      render: ({ data }: { data: RiakModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('节点'),
      field: 'riak_node',
      render: ({ data }: { data: RiakModel }) => (
        <RenderNodeInstance
          role="riak_node"
          title={`【${data.cluster_name}】${t('节点')}`}
          clusterId={data.id}
          originalList={data.riak_node.map(nodeItem => ({
            ip: nodeItem.ip,
            port: nodeItem.port,
            status: nodeItem.status,
          }))}
          dataSource={ getRiakInstanceList } />
      ),
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 160,
      sort: true,
      render: ({ data }: { data: RiakModel }) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('操作'),
      width: 300,
      render: ({ data }: { data: RiakModel }) => (
        data.isOnline
          ? <>
              <OperationBtnStatusTips data={data}>
                <bk-button
                  text
                  theme="primary"
                  disabled={data.operationDisabled}
                  onClick={() => handleAddNodes(data)}
                >
                  { t('添加节点') }
                </bk-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data} class="ml-16">
                <bk-button
                  text
                  theme="primary"
                  disabled={data.operationDisabled}
                  onClick={() => handleDeleteNodes(data)}
                >
                  { t('删除节点') }
                </bk-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data} class="ml-16">
                <bk-button
                  text
                  theme="primary"
                  disabled={data.operationDisabled}
                  onclick={() => handlDisabled(data)}
                >
                  { t('禁用') }
                </bk-button>
              </OperationBtnStatusTips>
            </>
          : <>
              <OperationBtnStatusTips data={data}>
                <bk-button
                  text
                  theme="primary"
                  disabled={data.operationDisabled}
                  onclick={() => handleEnabled(data)}
                >
                  { t('启用') }
                </bk-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data} class="ml-16">
                <bk-button
                  text
                  theme="primary"
                  disabled={data.operationDisabled}
                  onclick={() => handleDelete(data)}
                >
                  { t('删除') }
                </bk-button>
              </OperationBtnStatusTips>
            </>
      ),
    },
  ];

  const serachData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名'),
      id: 'name',
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: 'IP',
      id: 'ip',
    },
  ];

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValues = ref([]);
  const deployTime = ref(['', ''] as [string, string]);
  const addNodeShow = ref(false);
  const deleteNodeShow = ref(false);
  const detailData = ref<RiakModel>();
  const selected = shallowRef<RiakModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));

  watch(isStretchLayoutOpen, (newVal) => {
    emits('detailOpenChange', newVal);
  });

  const setRowClass = (row: RiakModel) => {
    const classList = [];

    if (row.isNewRow) {
      classList.push('is-new');
    }
    if (!row.isOnline) {
      classList.push('is-offline');
    }
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }

    return classList.join(' ');
  };

  const toApply = () => {
    router.push({
      name: 'RiakApply',
      query: {
        bizId: currentBizId,
      },
    });
  };

  const handleSelection = (key: number[], list: Record<any, any>[]) => {
    selected.value = list as RiakModel[];
  };

  const toDetail = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleAddNodes = (data: RiakModel) => {
    detailData.value = data;
    addNodeShow.value = true;
  };

  const handleDeleteNodes = (data: RiakModel) => {
    detailData.value = data;
    deleteNodeShow.value = true;
  };

  const handlDisabled = (data: RiakModel) => {
    InfoBox({
      title: t('确定禁用该集群', { name: data.cluster_name }),
      subTitle: (
        <>
          <p>{ t('集群') }：<span class='info-box-cluster-name'>{ data.cluster_name }</span></p>
          <p>{ t('被禁用后将无法访问，如需恢复访问，可以再次「启用」') }</p>
        </>
      ),
      infoType: 'warning',
      confirmText: t('禁用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_DISABLE,
          details: {
            cluster_id: data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };

  const handleEnabled = (data: RiakModel) => {
    InfoBox({
      title: t('确定启用该集群'),
      subTitle: (
        <>
          <p>{ t('集群') }：<span class='info-box-cluster-name'>{ data.cluster_name }</span></p>
          <p>{ t('启用后将恢复访问') }</p>
        </>
      ),
      infoType: 'warning',
      confirmText: t('启用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_ENABLE,
          details: {
            cluster_id: data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };

  const handleDelete = (data: RiakModel) => {
    InfoBox({
      title: t('确定删除该集群'),
      subTitle: (
        <>
          <p>{ t('集群') } ：<span class='info-box-cluster-name'>{ data.cluster_name }</span> , { t('被删除后将进行以下操作') }</p>
          <p>1. { t('删除xx集群', [data.cluster_name]) }</p>
          <p>2. { t('删除xx实例数据，停止相关进程', [data.cluster_name]) }</p>
          <p>3. { t('回收主机') }</p>
        </>
      ),
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('删除'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.RIAK_CLUSTER_DESTROY,
          details: {
            cluster_id: data.id,
          },
        })
          .then((createTicketResult) => {
            fetchData();
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };

  const fetchData = (otherParamas: {
    status?: string
  } = {}) => {
    const params = {
      ...otherParamas,
      ...getSearchSelectorParams(searchValues.value),
    };
    const [startTime, endTime] = deployTime.value;
    if (startTime && endTime) {
      Object.assign(params, {
        start_time: dayjs(startTime).format('YYYY-MM-DD'),
        end_time: dayjs(endTime).format('YYYY-MM-DD '),
      });
    }

    tableRef.value!.fetchData({ ...params }, {});
  };

  const handleColunmFilter = ({ checked }: { checked: string[] }) => {
    fetchData({ status: checked.join(',') });
  };

  onMounted(() => {
    fetchData();
    if (!clusterId.value && route.query.id) {
      toDetail(Number(route.query.id));
    }
  });

  defineExpose<Expose>({
    freshData() {
      fetchData();
    },
  });
</script>

<style>
.info-box-cluster-name {
  color: #313238;
}
</style>

<style lang="less" scoped>
.riak-list-container {
  height: 100%;
  overflow: hidden;

  .header-action {
    display: flex;
    margin-bottom: 16px;

    .header-action-search-select {
      width: 500px;
      margin-left: auto;
    }

    .header-action-deploy-time {
      width: 300px;
      margin-left: 8px;
    }
  }

  :deep(.riak-list-table) {
    .is-new {
      td {
        background-color: #F3FCF5 !important;
      }
    }

    .is-offline {
      .cell {
        color: #C4C6CC !important;
      }
    }

    .new-tag {
      height: 19px;
    }

    .disabled-tag {
      width: 38px;
      height: 16px;
      margin-left: 4px;
    }

    .db-icon-copy {
      display: none;
    }

    tr:hover {
      .db-icon-copy {
        display: inline-block !important;
        margin-left: 4px;
        color: #3a84ff;
        vertical-align: middle;
        cursor: pointer;
      }
    }
  }
}
</style>
