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
          disabled: hasSelected,
        }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelected"
          @click="handleBatchStopInstance">
          {{ t('禁用') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: hasSelected,
        }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelected"
          @click="handleBatchDeleteInstance">
          {{ t('删除') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择实例'),
          disabled: hasSelected,
        }"
        class="inline-block">
        <BkDropdown
          :popover-options="{
            clickContentAutoHide: true,
          }"
          trigger="click">
          <BkButton
            class="dropdown-button"
            :disabled="!hasSelected">
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
          style="width: 500px"
          :validate-values="validateValues"
          @change="fetchTableData" />
      </div>
    </div>
    <BkAlert
      v-if="tableDataCount === 0 && runningTicketList.length > 0"
      style="margin-bottom: 16px"
      theme="warning">
      <template #title>
        <div>
          {{ t('已有n个订阅单据正在进行中', { n: runningTicketList.length }) }}
          <BkButton
            v-for="item in runningTicketList"
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
      :bk-ui-settings="settings"
      class="table-box mb-24"
      :data-source="listDumperInstance"
      :row-class-name="setRowClass"
      row-key="id"
      selectable
      @clear-search="handleClearFilters"
      @filter-change="handleTableFilterChange"
      @request-success="handleTableRequestSuccess"
      @selection="handleSelect">
      <TableColumn
        col-key="instance"
        :ellipsis="false"
        fixed="left"
        :min-width="200"
        :title="t('实例')"
        :width="230">
        <template #default="{ row }: { row: DumperInstanceModel }">
          <TextOverflowLayout>
            <span class="mr-4">{{ `${row.ip}:${row.listen_port}` }}</span>
            <template #append>
              <BkPopover
                v-if="row.need_transfer"
                placement="top"
                :popover-delay="[100, 200]"
                theme="light">
                <DbIcon
                  class="migrate-fail-tip"
                  type="exclamation-fill" />
                <template #content>
                  <div>{{ t('Dumper实例迁移失败') }}</div>
                </template>
              </BkPopover>
              <RenderOperationTagNew :data="row.operationTagTip" />
              <MiniTag
                v-if="!row.isOnline && !row.isStarting"
                :content="t('已禁用')"
                ext-cls="stoped-icon" />
              <MiniTag
                v-if="row.isNew"
                content="NEW"
                ext-cls="success-icon"
                theme="success" />
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="dumper_id"
        :title="t('实例 ID')"
        :width="80">
      </TableColumn>
      <TableColumn
        col-key="source_cluster"
        :min-width="200"
        :title="t('数据源集群')"
        :width="250">
        <template #default="{ row }: { row: DumperInstanceModel }">
          <AuthRouterLink
            v-if="row.source_cluster"
            action-id="mysql_view"
            :permission="row.permission.mysql_view"
            :resource="row.source_cluster.id"
            target="_blank"
            :to="{
              name: 'DatabaseTendbha',
              query: {
                id: row.id,
              },
            }">
            {{ row.source_cluster.immute_domain }}:{{ row.source_cluster.master_port }}
          </AuthRouterLink>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="protocol_type"
        :filter="{
          list: [
            { label: 'KAFKA', value: 'KAFKA' },
            { label: 'L5_AGENT', value: 'L5_AGENT' },
            { label: 'TCP/IP', value: 'TCP/IP' },
          ],
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :title="t('接收端类型')">
      </TableColumn>
      <TableColumn
        col-key="receiver"
        :title="t('接收端地址')">
        <template #default="{ row }: { row: DumperInstanceModel }">
          <span>{{ row.target_address }}:{{ row.target_port }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="add_type"
        :filter="{
          list: [
            { label: t('全量同步'), value: 'full_sync' },
            { label: t('增量同步'), value: 'incr_sync' },
          ],
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :title="t('同步方式')">
        <template #default="{ row }: { row: DumperInstanceModel }">
          <span>{{ syncTypeMap[row.add_type] }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="isCN ? 160 : 220">
        <template #default="{ row }: { row: DumperInstanceModel }">
          <OperationBtnTip
            :data="row"
            :disabled="!row.isOperating">
            <span>
              <AuthButton
                action-id="tbinlogdumper_enable_disable"
                class="mr-8"
                :disabled="row.isOperating"
                :permission="row.permission.tbinlogdumper_enable_disable"
                :resource="row.cluster_id"
                text
                theme="primary"
                @click="() => handleOpenOrCloseInstance(row)">
                {{ row.isOnline ? t('禁用') : t('启用') }}
              </AuthButton>
            </span>
          </OperationBtnTip>
          <OperationBtnTip
            v-if="!row.isOnline"
            :data="row"
            :disabled="!row.isOperating">
            <span>
              <AuthButton
                action-id="tbinlogdumper_reduce_nodes"
                class="mr-8"
                :disabled="row.isOperating"
                :permission="row.permission.tbinlogdumper_reduce_nodes"
                :resource="row.cluster_id"
                text
                theme="primary"
                @click="() => handleDeleteInstance(row)">
                {{ t('删除') }}
              </AuthButton>
            </span>
          </OperationBtnTip>
          <OperationBtnTip
            v-if="row.need_transfer && row.source_cluster"
            :data="row"
            :disabled="!row.isOperating">
            <span>
              <AuthButton
                action-id="tbinlogdumper_switch_nodes"
                :disabled="row.isOperating"
                :permission="row.permission.tbinlogdumper_switch_nodes"
                :resource="row.cluster_id"
                text
                theme="primary"
                @click="() => handleOpenManualMigration(row)">
                {{ t('手动迁移') }}
              </AuthButton>
            </span>
          </OperationBtnTip>
        </template>
      </TableColumn>
    </DbTable>
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
  import { getRunningTaskList, listDumperConfig, listDumperInstance } from '@services/source/dumper';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';
  import { ipPort, ipv4 } from '@common/regex';

  import DbTable from '@components/db-table/IndexNew.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import RenderOperationTagNew from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  import AppendSubscribeSlider from '../append-subscribe/Index.vue';

  import ManualMigration from './manual-migration/Index.vue';
  import OperationBtnTip from './OperationBtnTip.vue';

  export type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number];

  interface Props {
    data: DumperConfig | null;
  }

  const props = defineProps<Props>();

  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const { locale, t } = useI18n();
  const router = useRouter();

  const searchSelectData = [
    {
      id: 'address',
      name: t('实例'),
    },
    {
      id: 'ip',
      name: 'IP',
    },
    {
      id: 'dumper_id',
      name: t('实例ID'),
    },
    {
      id: 'source_cluster',
      name: t('数据源集群'),
    },
    {
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
      id: 'protocol_type',
      multiple: true,
      name: t('接收端类型'),
    },
    {
      id: 'target_address',
      name: t('接收端地址'),
    },
    {
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
      id: 'add_type',
      multiple: true,
      name: t('同步方式'),
    },
  ];

  const tableRef = ref();
  const search = ref<ISearchValue[]>([]);
  const tableDataCount = ref(0);
  const showAppendSubscribeSlider = ref(false);
  const showManualMigration = ref(false);
  const activeRow = ref<DumperInstanceModel>();
  const runningTicketList = ref<number[]>([]);

  const selectedList = shallowRef<DumperInstanceModel[]>([]);

  const hasSelected = computed(() => selectedList.value.length > 0);

  const isCN = computed(() => locale.value === 'zh-cn');

  const syncTypeMap = {
    full_sync: t('全量同步'),
    incr_sync: t('增量同步'),
  } as Record<string, string>;

  const settings = {
    checked: ['instance', 'dumper_id', 'source_cluster', 'protocol_type', 'receiver', 'add_type'],
    disabled: ['instance'],
  };

  const { run: fetchRunningTaskList } = useRequest(getRunningTaskList, {
    manual: true,
    onSuccess(result) {
      runningTicketList.value = result;
    },
  });

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
    tableRef.value?.fetchData({
      ...searchParams,
      config_name: props.data === null ? undefined : props.data.name,
    });
  };

  watch(
    () => [props.data, search],
    () => {
      fetchTableData();
      // tableRef.value?.clearSelected();
      if (props.data) {
        fetchRunningTaskList({
          dumper_config_id: props.data?.id,
        });
      }
    },
    {
      immediate: true,
    },
  );

  // tip: async 去掉组件库会报错
  const validateValues = async (item: { id: string }, values: ISearchValue['values']) => {
    if (values) {
      const targetValue = values[0].id.replace(/^\s+|\s+$/g, '');
      if (item.id === 'address') {
        const list = targetValue.split(',');
        if (list.some((item) => !ipPort.test(item))) {
          return t('格式错误');
        }
      }
      if (item.id === 'ip' && !ipv4.test(targetValue)) {
        return t('格式错误');
      }
      return true;
    }
    return false;
  };

  const handleGoTicket = (ticketId?: number) => {
    if (!ticketId) {
      return;
    }
    const route = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId,
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
    if (data.isOnline) {
      InfoBox({
        confirmText: t('禁用'),
        content: (
          <div>
            <div>
              {t('实例')}：{data.ip}:{data.listen_port}
            </div>
            <div style='margin-top: 8px;'>{t('禁用后数据传输将会终止，请谨慎操作！')}</div>
          </div>
        ),
        infoType: 'warning',
        onConfirm: () => {
          const params = {
            bk_biz_id: currentBizId,
            details: {
              dumper_instance_ids: [data.id],
            },
            remark: '',
            ticket_type: TicketTypes.TBINLOGDUMPER_DISABLE_NODES,
          };
          runCreateTicket(params);
        },
        title: t('确认禁用该实例？'),
        width: 400,
      });
      return;
    }
    // 启用
    const params = {
      bk_biz_id: currentBizId,
      details: {
        dumper_instance_ids: [data.id],
      },
      remark: '',
      ticket_type: TicketTypes.TBINLOGDUMPER_ENABLE_NODES,
    };
    runCreateTicket(params);
  };

  // 批量禁用
  const handleBatchStopInstance = () => {
    InfoBox({
      confirmText: t('禁用'),
      extCls: 'dumper-instance-infobox',
      infoType: 'warning',
      onConfirm: () => {
        const params = {
          bk_biz_id: currentBizId,
          details: {
            dumper_instance_ids: selectedList.value.map((item) => item.id),
          },
          remark: '',
          ticket_type: TicketTypes.TBINLOGDUMPER_DISABLE_NODES,
        };
        runCreateTicket(params);
      },
      subTitle: t('禁用后数据传输将会终止，请谨慎操作！'),
      title: t('确认批量禁用n个实例？', { n: selectedList.value.length }),
      width: 400,
    });
  };

  // 删除
  const handleDeleteInstance = (data: DumperInstanceModel) => {
    if (data.isOperating) {
      return;
    }
    InfoBox({
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      content: (
        <div class='dumper-instance-infobox-subtitle'>
          <div>
            {t('实例')}：{data.ip}:{data.listen_port}
          </div>
          <div style='margin-top: 8px;'>{t('删除后数据传输将会终止，并删除实例，请谨慎操作！')}</div>
        </div>
      ),
      onConfirm: () => {
        const params = {
          bk_biz_id: currentBizId,
          details: {
            dumper_instance_ids: [data.id],
          },
          remark: '',
          ticket_type: TicketTypes.TBINLOGDUMPER_REDUCE_NODES,
        };
        runCreateTicket(params);
      },
      type: 'warning',
      width: 400,
    });
  };

  // 批量删除
  const handleBatchDeleteInstance = () => {
    InfoBox({
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      content: t('删除后数据传输将会终止，并删除实例，请谨慎操作！'),
      onConfirm: () => {
        const params = {
          bk_biz_id: currentBizId,
          details: {
            dumper_instance_ids: selectedList.value.map((item) => item.id),
          },
          remark: '',
          ticket_type: TicketTypes.TBINLOGDUMPER_REDUCE_NODES,
        };
        runCreateTicket(params);
      },
      title: t('确认批量删除n个实例？', { n: selectedList.value.length }),
      type: 'warning',
      width: 400,
    });
  };

  const handleOpenManualMigration = (data: DumperInstanceModel) => {
    if (data.isOperating) {
      return;
    }
    activeRow.value = data;
    showManualMigration.value = true;
  };

  const handleTableRequestSuccess = (data: ServiceReturnType<typeof listDumperInstance>) => {
    tableDataCount.value = data.results.length;
  };

  // 设置行样式
  const setRowClass = ({ row }: { row: DumperInstanceModel }) => {
    const rowClasses: string[] = [];
    if (row.isNew) {
      rowClasses.push('is-new-row');
    }
    if (!row.isOnline) {
      rowClasses.push('is-stoped');
    }
    return rowClasses.join(' ');
  };

  const handleClearFilters = () => {
    search.value = [];
    fetchTableData();
  };

  const handleCopyAll = (isInstance = false) => {
    const list = (tableRef.value.getData() as DumperInstanceModel[]).map((item) => `${item.ip}:${item.listen_port}`);
    if (!isInstance) {
      copy(list.map((inst) => inst.split(':')[0]));
      return;
    }
    copy(list);
  };

  const handleCopySelected = (isInstance = false) => {
    const list = selectedList.value.map((item) => `${item.ip}:${item.listen_port}`);
    if (!isInstance) {
      copy(list.map((inst) => inst.split(':')[0]));
      return;
    }

    copy(list);
  };

  const copy = (value: string[]) => {
    execCopy(value.join(','), t('复制成功，共n条', { n: value.length }));
  };

  // 选择单台
  const handleSelect = (_idList: string[], list: DumperInstanceModel[]) => {
    selectedList.value = list;
  };

  const handleTableFilterChange = (filterValue: Record<string, string[]>) => {
    const filterFieldNameMap: Record<string, string> = {
      add_type: t('同步方式'),
      protocol_type: t('接收端类型'),
    };
    const filterFields = Object.keys(filterFieldNameMap);
    const otherSearchValues = search.value.filter((item) => !filterFields.includes(item.id));
    const filterSearchValues = filterFields
      .filter((field) => filterValue[field]?.length)
      .map((field) => ({
        id: field,
        name: filterFieldNameMap[field],
        values: filterValue[field].map((item) => ({
          id: item,
          name: field === 'add_type' ? syncTypeMap[item] : item,
        })),
      }));
    search.value = [...otherSearchValues, ...filterSearchValues];
  };
</script>

<style lang="less">
  .dumper-instance-status-migrate {
    color: #8e3aff;
    background-color: #f2edff;
  }

  .dumper-instance-list {
    height: 100%;
    background-color: white;

    .table-box {
      .is-stoped {
        td {
          color: #c4c6cc !important;
        }
      }

      .migrate-fail-tip {
        margin-right: 4px;
        font-size: 13px;
        color: #ff9c01;
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

    .is-offline {
      a {
        color: @gray-color;
      }

      td {
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
