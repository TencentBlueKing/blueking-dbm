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
  <div class="dumper-instance-list">
    <div class="instances-view-operations">
      <BkButton
        v-if="data !== null"
        theme="primary"
        @click="handleAppendInstance">
        {{ t('追加订阅') }}
      </BkButton>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: hasSelectedInstances,
        }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelectedInstances"
          @click="handleBatchStopInstance">
          {{ t('禁用') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: hasSelectedInstances,
        }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelectedInstances"
          @click="handleBatchDeleteInstance">
          {{ t('删除') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: hasSelectedInstances,
        }"
        class="inline-block">
        <BkDropdown :disabled="!hasSelectedInstances">
          <BkButton
            class="dropdown-button"
            :disabled="!hasSelectedInstances">
            {{ t('复制') }}
            <DbIcon type="up-big dropdown-button-icon" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleCopyAll()">
                {{ t('所有IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAll(true)">
                {{ t('所有实例') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopySelected()">
                {{ t('已选IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopySelected(true)">
                {{ t('已选实例') }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </span>
      <div class="instances-view-operations-right">
        <DbSearchSelect
          v-model="search"
          clearable
          :data="searchSelectData"
          :placeholder="t('请选择条件搜索')"
          style="width: 500px;"
          :validate-values="validateValues"
          @change="fetchTableData" />
      </div>
    </div>
    <BkAlert
      v-if="tableDataCount === 0 && runningTickets.length > 0"
      style="margin-bottom: 16px;"
      theme="warning">
      <template #title>
        <div>
          {{ t('已有n个订阅单据正在进行中', {n: data?.running_tickets?.length ?? 0}) }}
          <BkButton
            v-for="item in data?.running_tickets"
            :key="item"
            class="mr-8"
            text
            theme="primary"
            @click="() => handleGoTicket(item)">
            {{ item }}
          </BkButton>
        </div>
      </template>
    </BkAlert>
    <DbTable
      ref="tableRef"
      class="table-box"
      :clear-selection="false"
      :columns="columns"
      :data-source="listDumperInstance"
      :row-class="setRowClass"
      selection-key="dumper_id"
      :settings="settings"
      style="margin-bottom: 34px;"
      @clear-search="handleClearFilters"
      @column-filter="handleColumnFilter"
      @request-finished="handleTableRequestFinished"
      @select="handleSelect"
      @select-all="handleSelectAll" />
  </div>
  <AppendSubscribeSlider
    v-model="showAppendSubscribeSlider"
    :data="data" />
  <ManualMigration
    v-if="activeRow"
    v-model="showManualMigration"
    :data="activeRow"
    @success="fetchTableData" />
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DumperInstanceModel from '@services/model/dumper/dumper';
  import {
    listDumperConfig,
    listDumperInstance,
  } from '@services/source/dumper';
  import { createTicket } from '@services/source/ticket';

  import {
    useCopy,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';
  import {
    ipPort,
    ipv4,
  } from '@common/regex';

  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import AppendSubscribeSlider from '../append-subscribe/Index.vue';

  import ManualMigration from './manual-migration/Index.vue';
  import OperationBtnTip from './OperationBtnTip.vue';


  export type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number]

  interface Props {
    data: DumperConfig | null
  }

  const props = defineProps<Props>();

  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const { t, locale } = useI18n();
  const copy = useCopy();
  const router = useRouter();

  const searchSelectData = [
    {
      name: t('实例'),
      id: 'address',
    },
    {
      name: 'IP',
      id: 'ip',
    },
    {
      name: t('实例ID'),
      id: 'dumper_id',
    },
    {
      name: t('数据源集群'),
      id: 'source_cluster',
    },
    {
      name: t('接收端类型'),
      id: 'protocol_type',
      multiple: true,
      children: [
        {
          id: 'KAFKA',
          name: 'KAFKA',
        },
        {
          id: 'L5_AGENT',
          name: 'L5_AGENT',
        },
        {
          id: 'TCP/IP',
          name: 'TCP/IP',
        },
      ],
    },
    {
      name: t('接收端地址'),
      id: 'target_address',
    },
    {
      name: t('同步方式'),
      id: 'add_type',
      multiple: true,
      children: [
        {
          id: 'full_sync',
          name: t('全量同步'),
        },
        {
          id: 'incr_sync',
          name: t('增量同步'),
        },
      ],
    },
  ];

  const tableRef = ref();
  const search = ref<ISearchValue[]>([]);
  const tableDataCount = ref(0);
  const showAppendSubscribeSlider = ref(false);
  const showManualMigration = ref(false);
  const activeRow = ref<DumperInstanceModel>();

  const batchSelectInstances = shallowRef<Record<number, DumperInstanceModel>>({});

  const selectedInstances = computed(() => Object.entries(batchSelectInstances.value));

  const hasSelectedInstances = computed(() => selectedInstances.value.length > 0);
  const runningTickets = computed(() => props.data?.running_tickets ?? []);
  const isCN = computed(() => locale.value === 'zh-cn');

  const syncTypeMap = {
    full_sync: t('全量同步'),
    incr_sync: t('增量同步'),
  } as Record<string, string>;

  const columns = [
    {
      type: 'selection',
      width: 30,
      minWidth: 30,
      label: '',
      fixed: 'left',
    },
    {
      label: t('实例'),
      minWidth: 200,
      width: 230,
      fixed: 'left',
      field: 'instance',
      showOverflowTooltip: false,
      render: ({ data }: {data: DumperInstanceModel}) => {
        const content = <>
          {data.need_transfer && (
            <bk-popover
              placement="top"
              theme="light"
              popover-delay={[100, 200]}
            >
            {{
              default: () => <db-icon class="migrate-fail-tip" type='exclamation-fill' />,
              content: () => <div>{t('Dumper实例迁移失败')}</div>,
            }}
            </bk-popover>
          )}
          <RenderOperationTag data={data.operationTagTip} />
          {!data.isRunning && <MiniTag content={t('已禁用')} extCls='stoped-icon'/>}
          {data.isNew && <MiniTag theme='success' content="NEW" extCls='success-icon' />}
        </>;
        return (
          <div class="instance-box">
            <RenderTextEllipsisOneLine
              key={data.operation.ticket_type}
              text={`${data.ip}:${data.listen_port}`}
              textStyle={{ color: '#63656E' }}>
              {content}
            </RenderTextEllipsisOneLine>
          </div>
        );
      },
    },
    {
      label: t('实例 ID'),
      field: 'dumper_id',
      width: 80,
    },
    {
      label: t('数据源集群'),
      field: 'source_cluster',
      minWidth: 200,
      width: 250,
      render: ({ data }: {data: DumperInstanceModel}) => (data.source_cluster ? (
        <bk-button
          class="source-cluster-btn"
          text
          theme="primary"
          onClick={() => handleOpenClusterDetailPage(data.source_cluster!.id)}>
          {data.source_cluster.immute_domain}:{data.source_cluster.master_port}
        </bk-button>) : '--'
      ),
    },
    {
      label: t('接收端类型'),
      field: 'protocol_type',
      filter: {
        list: [
          { text: 'KAFKA', value: 'KAFKA' },
          { text: 'L5_AGENT', value: 'L5_AGENT' },
          { text: 'TCP/IP', value: 'TCP/IP' },
        ],
      },
    },
    {
      label: t('接收端地址'),
      field: 'receiver',
      render: ({ data }: {data: DumperInstanceModel}) => <span>{data.target_address}:{data.target_port}</span>,
    },
    {
      label: t('同步方式'),
      field: 'add_type',
      filter: {
        list: [
          { text: t('全量同步'), value: 'full_sync' },
          { text: t('增量同步'), value: 'incr_sync' },
        ],
      },
      render: ({ data }: {data: DumperInstanceModel}) => <span>{syncTypeMap[data.add_type]}</span>,
    },
    {
      label: t('操作'),
      field: '',
      fixed: 'right',
      width: isCN.value ? 160 : 220,
      render: ({ data }: {data: DumperInstanceModel}) => (
        <>
          <OperationBtnTip
            data={data}
            disabled={!data.isOperating}>
            <span>
              <bk-button
              text
              disabled={data.isOperating}
              class='mr-8'
              theme="primary"
              onClick={() => handleOpenOrCloseInstance(data)}>
                { data.isRunning ? t('禁用') : t('启用') }
            </bk-button>
            </span>
          </OperationBtnTip>
          {!data.isRunning && (
            <OperationBtnTip
              data={data}
              disabled={!data.isOperating}>
              <span>
                <bk-button
                  text
                  disabled={data.isOperating}
                  class='mr-8'
                  theme="primary"
                  onClick={() => handleDeleteInstance(data)}>
                    { t('删除') }
                </bk-button>
              </span>
            </OperationBtnTip>
          )}
          {data.need_transfer && (
            <OperationBtnTip
              data={data}
              disabled={!data.isOperating}>
              <span>
                <bk-button
                  text
                  disabled={data.isOperating}
                  theme="primary"
                  onClick={() => handleOpenManualMigration(data)}>
                    { t('手动迁移') }
                </bk-button>
              </span>
            </OperationBtnTip>
          )}
        </>
      ),
    },
  ];

  const settings = {
    fields: [
      {
        label: t('实例'),
        field: 'instance',
        disabled: true,
      },
      {
        label: t('实例 ID'),
        field: 'dumper_id',
      },
      {
        label: t('数据源集群'),
        field: 'source_cluster',
      },
      {
        label: t('接收端类型'),
        field: 'protocol_type',
      },
      {
        label: t('接收端地址'),
        field: 'receiver',
      },
      {
        label: t('同步方式'),
        field: 'add_type',
      },
    ],
    checked: ['instance', 'dumper_id', 'source_cluster', 'protocol_type', 'receiver', 'add_type'],
  };

  const { run: runCreateTicket } = useRequest(createTicket, {
    manual: true,
    onSuccess: (data) => {
      if (data && data.id) {
        ticketMessage(data.id);
        fetchTableData();
      }
    },
  });

  const fetchTableData = () => {
    const searchParams = getSearchSelectorParams(search.value);
    tableRef.value?.fetchData(searchParams, {
      config_name: props.data === null ? undefined : props.data.name,
    });
  };

  watch(() => [props.data, search], () => {
    fetchTableData();
  }, {
    immediate: true,
  });

  // tip: async 去掉组件库会报错
  const validateValues = async (item: {id: string}, values: ISearchValue['values']) => {
    if (values) {
      const targetValue = values[0].id.replace(/^\s+|\s+$/g, '');
      if (item.id === 'address') {
        const list = targetValue.split(',');
        if (list.some(item => !ipPort.test(item))) {
          return t('格式错误');
        }
      }
      if (item.id === 'ip' && !ipv4.test(targetValue)) {
        return t('格式错误');
      }
      return  true;
    }
    return false;
  };

  const handleOpenClusterDetailPage = (id: number) => {
    const routerData = router.resolve({
      name: 'DatabaseTendbha',
      query: {
        id,
      },
    });
    window.open(routerData.href);
  };

  const handleGoTicket = (ticketId?: number) => {
    if (!ticketId) {
      return;
    }
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id: ticketId,
      },
    });
    window.open(route.href);
  };

  const handleAppendInstance = () => {
    showAppendSubscribeSlider.value = true;
  };

  const handleOpenOrCloseInstance = (data: DumperInstanceModel) => {
    if (data.isOperating) {
      return;
    }
    if (data.isRunning) {
      InfoBox({
        extCls: 'dumper-instance-infobox',
        infoType: 'warning',
        title: t('确认禁用该实例？'),
        confirmText: t('禁用'),
        subTitle: <div class="dumper-instance-infobox-subtitle">
          <div>{t('实例')}：{data.ip}:{data.listen_port}</div>
          <div style="margin-top: 8px;">{t('禁用后数据传输将会终止，请谨慎操作！')}</div>
        </div>,
        width: 400,
        onConfirm: () => {
          const params = {
            bk_biz_id: currentBizId,
            ticket_type: TicketTypes.TBINLOGDUMPER_DISABLE_NODES,
            remark: '',
            details: {
              dumper_instance_ids: [data.id],
            },

          };
          runCreateTicket(params);
        } });
      return;
    }
    // 启用
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.TBINLOGDUMPER_ENABLE_NODES,
      remark: '',
      details: {
        dumper_instance_ids: [data.id],
      },

    };
    runCreateTicket(params);
  };

  // 批量禁用
  const handleBatchStopInstance = () => {
    InfoBox({
      extCls: 'dumper-instance-infobox',
      infoType: 'warning',
      title: t('确认批量禁用n个实例？', { n: selectedInstances.value.length }),
      confirmText: t('禁用'),
      subTitle: t('禁用后数据传输将会终止，请谨慎操作！'),
      width: 400,
      onConfirm: () => {
        const params = {
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.TBINLOGDUMPER_DISABLE_NODES,
          remark: '',
          details: {
            dumper_instance_ids: selectedInstances.value.map(item => item[0]),
          },

        };
        runCreateTicket(params);
      } });
  };

  // 删除
  const handleDeleteInstance = (data: DumperInstanceModel) => {
    if (data.isOperating) {
      return;
    }
    InfoBox({
      infoType: 'warning',
      extCls: ['dumper-instance-infobox', 'dumper-instance-infobox-delete'],
      title: t('确认删除该实例？'),
      confirmText: t('删除'),
      subTitle: <div class="dumper-instance-infobox-subtitle">
          <div>{t('实例')}：{data.ip}:{data.listen_port}</div>
          <div style="margin-top: 8px;">{t('删除后数据传输将会终止，并删除实例，请谨慎操作！')}</div>
        </div>,
      width: 400,
      onConfirm: () => {
        const params = {
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.TBINLOGDUMPER_REDUCE_NODES,
          remark: '',
          details: {
            dumper_instance_ids: [data.id],
          },

        };
        runCreateTicket(params);
      } });
  };

  // 批量删除
  const handleBatchDeleteInstance = () => {
    InfoBox({
      infoType: 'warning',
      extCls: ['dumper-instance-infobox', 'dumper-instance-infobox-delete'],
      title: t('确认批量删除n个实例？', { n: selectedInstances.value.length }),
      confirmText: t('删除'),
      subTitle: t('删除后数据传输将会终止，并删除实例，请谨慎操作！'),
      width: 400,
      onConfirm: () => {
        const params = {
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.TBINLOGDUMPER_REDUCE_NODES,
          remark: '',
          details: {
            dumper_instance_ids: selectedInstances.value.map(item => item[0]),
          },

        };
        runCreateTicket(params);
      } });
  };

  const handleOpenManualMigration = (data: DumperInstanceModel) => {
    if (data.isOperating) {
      return;
    }
    activeRow.value = data;
    showManualMigration.value = true;
  };

  const handleTableRequestFinished = (data: any[]) => {
    tableDataCount.value = data.length;
  };

  // 设置行样式
  const setRowClass = (row: DumperInstanceModel) => {
    const rowClasses: string[] = [];
    if (row.isNew) {
      rowClasses.push('is-new-row');
    }
    if (!row.isRunning) {
      rowClasses.push('is-stoped');
    }
    return rowClasses.join(' ');
  };

  const handleClearFilters = () => {
    search.value = [];
    fetchTableData();
  };

  const handleCopyAll = (isInstance = false) => {
    const list = (tableRef.value.getData() as DumperInstanceModel[]).map(item => `${item.ip}:${item.listen_port}`);
    if (!isInstance) {
      copy(list.map(inst => inst.split(':')[0]).join(','));
      return;
    }
    copy(list.join(','));
  };

  const handleCopySelected = (isInstance = false) => {
    const list = Object.values(batchSelectInstances.value).map(item => `${item.ip}:${item.listen_port}`);
    if (!isInstance) {
      copy(list.map(inst => inst.split(':')[0]).join(','));
      return;
    }

    copy(list.join(','));
  };

  // 选择单台
  const handleSelect = (data: { checked: boolean, row: DumperInstanceModel }) => {
    const selectedMap = { ...batchSelectInstances.value };
    if (data.checked) {
      selectedMap[data.row.id] = data.row;
    } else {
      delete selectedMap[data.row.id];
    }

    batchSelectInstances.value = selectedMap;
  };

  // 选择所有
  const handleSelectAll = (data:{checked: boolean}) => {
    let selectedMap = { ...batchSelectInstances.value };
    if (data.checked) {
      selectedMap = (tableRef.value.getData() as DumperInstanceModel[]).reduce((result, item) => ({
        ...result,
        [item.id]: item,
      }), {});
    } else {
      selectedMap = {};
    }
    batchSelectInstances.value = selectedMap;
  };

  const handleColumnFilter = (data: {
    checked: string[],
    column: {
      field: string,
      label: string,
    },
    index: number,
  }) => {
    if (data.checked.length === 0) {
      search.value = search.value.filter(item => item.id !== data.column.field);
      return;
    }
    const isAddType = data.column.field === 'add_type';
    search.value = [{
      id: data.column.field,
      name: data.column.label,
      values: data.checked.map(item => ({
        id: item,
        name: isAddType ? syncTypeMap[item] : item,
      })),
    }];
  };

</script>

<style lang="less">

.dumper-instance-infobox {
  .bk-modal-body {
    .bk-modal-content {
      padding: 0 24px 30px;
    }

    .bk-modal-footer {
      height: 56px;
    }
  }
}

.dumper-instance-infobox-delete {
  .bk-modal-body {
    .bk-modal-footer {
      .bk-button-primary {
        background-color: #EA3636;
        border: none;
      }
    }
  }
}

.dumper-instance-infobox-subtitle {
  display: flex;
  width: 100%;
  justify-content: center;
  flex-direction: column;
}

.dumper-instance-status-migrate {
  color: #8E3AFF;
  background-color: #F2EDFF;
}

.dumper-instance-list {
  height: 100%;
  background-color: white;

  .table-box {
    .is-stoped {
      td {
        .cell {
          color: #C4C6CC !important;
        }

      }
    }

    .migrate-fail-tip {
      margin-right: 4px;
      font-size: 13px;
      color: #FF9C01;
    }
  }


  tr {
    &:hover {
      .db-icon-copy {
        display: inline-block;
      }
    }
  }

  .instances-view-header {
    display: flex;
    height: 20px;
    color: @title-color;
    align-items: center;

    .instances-view-header-icon {
      font-size: 18px;
      color: @gray-color;
    }
  }

  .instances-view-operations {
    display: flex;
    align-items: center;
    padding: 16px 0;

    .instances-view-operations-right {
      flex: 1;
      display: flex;
      justify-content: flex-end;
    }

    .bk-button {
      margin-right: 8px;
    }

    .dropdown-button {
      .dropdown-button-icon {
        margin-left: 6px;
        transition: all 0.2s;
      }

      &.active:not(.is-disabled) {
        .dropdown-button-icon {
          transform: rotate(180deg);
        }
      }
    }
  }

  .instance-box {
    display: flex;
    align-items: center;
    padding: 8px 0;
    overflow: hidden;

    .stoped-icon {
      &:hover {
        background-color: #f0f1f5;
      }
    }

    .success-icon {
      &:hover {
        background-color: #e4faf0;
      }
    }

    .instance-name {
      margin-right: 3px;
      line-height: 20px;
    }

    .cluster-tags {
      display: flex;
      margin-left: 4px;
      align-items: center;
      flex-wrap: wrap;
    }

    .cluster-tag {
      margin: 2px;
      flex-shrink: 0;
    }

    .db-icon-copy {
      display: none;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }

  .source-cluster-btn {
    width: auto;
    max-width: 100%;
    overflow: hidden;

    .bk-button-text {
      width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .is-offline {
    a {
      color: @gray-color;
    }

    .cell {
      color: @disable-color !important;
    }
  }
}

.bk-dropdown-item {
  &.is-disabled {
    color: @disable-color;
    cursor: not-allowed;
  }
}
</style>
