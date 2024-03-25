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
  <div class="ticket-flow-list-content">
    <div class="top-operation">
      <span
        v-bk-tooltips="{
          disabled: hasSelected,
          content: t('请选择单据'),
        }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelected"
          theme="primary"
          @click="handleBatchEdit">
          {{ t('批量编辑') }}
        </BkButton>
      </span>
      <BkSearchSelect
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList"
        :placeholder="t('请选择条件搜索')"
        unique-select
        value-split-code="+"
        @search="fetchHostNodes" />
    </div>
    <BkLoading :loading="isTableLoading">
      <DbTable
        ref="tableRef"
        class="table-box"
        :columns="columns"
        :data-source="queryTicketFlowDescribe"
        primary-key="ticket_type"
        :remote-pagination="false"
        selectable
        @clear-search="handleClearSearch"
        @selection="handleSelection" />
    </BkLoading>
  </div>
  <BatchConfigDialog
    v-model:is-show="isShowBatchConfigDialog"
    :ticket-types="selecedTicketTypes"
    @success="handleBatchEditSuccess" />
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe'
  import {
    getTicketTypes,
    queryTicketFlowDescribe,
    updateTicketFlowConfig,
  } from '@services/source/ticket';

  import {
    messageSuccess,
  } from '@utils';

  import BatchConfigDialog from './BatchConfigDialog.vue';

  interface Props {
    activeDbType: string;
  }

  interface SearchSelectItem {
    id: string,
    name: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const isTableLoading = ref(false);
  const isShowBatchConfigDialog = ref(false);

  const ticketTypeList = shallowRef<{
    id: string;
    name: string;
  }[]>([]);

  const selected = shallowRef<TicketFlowDescribeModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selecedTicketTypes = computed(() => selected.value.map(item => item.ticket_type));

  const reqParams = computed(() => {
    const searchParams = searchValue.value.reduce((obj, item) => {
      Object.assign(obj, {
        [item.id]: item.values.map(data => data.id).join(','),
      });
      return obj;
    }, {} as Record<string, string>);
    return {
      ...searchParams,
    };
  });

  const searchSelectList = computed(() => ([
    {
      name: t('单据类型'),
      id: 'ticket_type',
      multiple: true,
      children: ticketTypeList.value,
    },
  ]));

  const configMap = {
    need_itsm: t('单据审批'),
    need_manual_confirm: t('人工确认'),
  };

  const columns = [
    {
      label: t('单据类型'),
      field: 'ticket_type_display',
    },
    {
      label: t('可增加的流程节点'),
      field: 'configs',
      render: ({ data }: { data: TicketFlowDescribeModel }) => (Object.keys(data.configs) as (keyof TicketFlowDescribeModel['configs'])[]).map((key) => (
        <bk-pop-confirm
          title={data.configs[key] ? t('确认删除“单据审批”流程节点？') : t('确认添加“单据审批”流程节点？')}
          content={
            <div class="ticket-flow-change-node-box">
              <div class="item-box">
                <div class="title">{t('单据类型')}：</div>
                <div class="content" style="color: #313238;">{data.ticket_type_display}</div>
              </div>
              <div class="item-box mb-16 mt-6">
                <div class="title">{t('流程预览')}：</div>
                <div class="content">{
                  <>
                    {
                      !data.configs[key] && <>
                        <span
                            class={{ 'add-node': !data.configs[key] }}>
                            {configMap[key]}
                          </span>
                          <span>{' -> '}</span>
                      </>
                    }
                    {
                      data.flow_desc.map((flow, index) => (
                        <>
                          <span
                            class={{ 'delete-node': data.configs[key] && configMap[key] === flow }}>
                            {flow}
                          </span>
                          <span>{index !== data.flow_desc.length - 1 ? ' -> ' : ''}</span>
                        </>
                      ))
                    }
                  </>
                  }
                </div>
              </div>
            </div>
          }
          width="400"
          placement="top"
          trigger="click"
          confirm-text={data.configs[key] ? t('删除') : t('确定')}
          onConfirm={() => handleConfirmCheck(data, key, !data.configs[key])}
        >
          <auth-template
            class="flow-node-action"
            action-id="ticket_config_set"
            resource={data.ticket_type}
            permission={data.permission.ticket_config_set}>
            <bk-checkbox
              modelValue={data.configs[key]}
              style="pointer-events: none;">
              {configMap[key]}
            </bk-checkbox>
          </auth-template>
        </bk-pop-confirm>
      )),
    },
    {
      label: t('流程预览'),
      field: 'flow_desc',
      showOverflowTooltip: true,
      width: 520,
      render: ({ data }: { data: TicketFlowDescribeModel }) => <span>{data.flow_desc.join(' -> ')}</span>,
    },
    {
      label: t('更新人'),
      field: 'updater',
      showOverflowTooltip: true,
      width: 180,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      render: ({ data }: { data: TicketFlowDescribeModel }) => data.updateAtDisplay,
    },
  ];

  async function fetchHostNodes() {
    isTableLoading.value = true;
    try {
      await tableRef.value.fetchData({ ...reqParams.value }, {
        db_type: props.activeDbType,
      });
    } finally {
      isTableLoading.value = false;
    }
  }

  const {
    run: runUpdateTicketFlowConfig,
  } = useRequest(updateTicketFlowConfig, {
    manual: true,
    onSuccess: (data) => {
      if (!data) {
        messageSuccess(t('操作成功'));
        fetchHostNodes();
      }
    },
  });

  useRequest(getTicketTypes, {
    onSuccess: (data) => {
      ticketTypeList.value = data.map(item => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  watch(reqParams, () => {
    fetchHostNodes();
  });

  watch(() => props.activeDbType, (type) => {
    if (type) {
      searchValue.value = [];
      fetchHostNodes();
    }
  });

  const handleConfirmCheck = _.debounce((
    row: TicketFlowDescribeModel,
    key: keyof TicketFlowDescribeModel['configs'],
    value: boolean) => {
      runUpdateTicketFlowConfig({
        ticket_types: [row.ticket_type],
        configs: {
          ...row.configs,
          [key]: value
        },
      });
    }, 500);

  const handleBatchEditSuccess = () => {
    fetchHostNodes();
  };

  const handleSelection = (data: TicketFlowDescribeModel, list: TicketFlowDescribeModel[]) => {
    selected.value = list;
  };

  const handleBatchEdit = () => {
    isShowBatchConfigDialog.value = true;
  };

  const handleClearSearch = () => {
    searchValue.value = [];
  };
</script>
<style lang="less" scoped>
  .ticket-flow-list-content {
    display: flex;
    padding: 24px;
    flex-direction: column;

    .top-operation {
      display: flex;
      width: 100%;
      height: 32px;
      justify-content: space-between;
      margin-bottom: 16px;

      .input-box {
        width: 600px;
        height: 32px;
        margin-bottom: 16px;
      }
    }

    :deep(.table-box) {
      .strategy-title {
        display: flex;

        .name {
          margin-left: 8px;
        }
      }

      .notify-box {
        display: inline-block;
        height: 22px;
        padding: 2.5px 5px;
        background: #f0f1f5;
        border-radius: 2px;

        .dba {
          margin-left: 8px;
        }
      }

      .operate-box {
        display: flex;
        align-items: center;
      }

      .is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }
    }
  }
</style>

<style lang="less">
  .flow-node-action{
      display: inline-block;
      cursor: pointer;

      & ~ .flow-node-action{
        margin-left: 24px;
      }
    }

  .ticket-flow-change-node-box {
    .item-box {
      display: flex;
      width: 100%;

      .title {
        width: 60px;
      }

      .content {
        flex: 1;
        height: auto;

        .add-node {
          color: #ff9c01;
        }

        .delete-node {
          color: #ea3636;
          text-decoration: line-through;
        }
      }
    }
  }
</style>
