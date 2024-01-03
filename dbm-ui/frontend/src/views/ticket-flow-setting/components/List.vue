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
          content: t('请选择单据')
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

  import {
    getTicketTypes,
    queryTicketFlowDescribe,
    updateTicketFlowConfig,
  } from '@services/source/ticket';

  import {
    messageSuccess,
    utcDisplayTime,
  } from '@utils';

  import BatchConfigDialog from './BatchConfigDialog.vue';

  export type RowData = ServiceReturnType<typeof queryTicketFlowDescribe>['results'][number];

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
  const currentChoosedRow = ref<RowData>();
  const currentFlow = ref('');
  const isTableLoading = ref(false);
  const isShowBatchConfigDialog = ref(false);

  const ticketTypeList = shallowRef<{
    id: string;
    name: string;
  }[]>([]);

  const selected = shallowRef<RowData[]>([]);

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

  const configMap: Record<string, string> = {
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
      render: ({ data }: { data: RowData }) => Object.keys(data.configs).map(key => (
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
                            {configMap[currentFlow.value]}
                          </span>
                          <span>{' -> '}</span>
                      </>
                    }
                    {
                      data.flow_desc.map((flow, index) => (
                        <>
                          <span
                            class={{ 'delete-node': data.configs[key] && configMap[currentFlow.value] === flow }}>
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
          onConfirm={() => handleConfirmCheck(data)}
        >
          <bk-checkbox
            v-model={data.configs[key]}
            immediateEmitChange={false}
            onChange={(checked: boolean) => handleCheckBoxValueChange(data, key, checked)}>
            {configMap[key]}
          </bk-checkbox>
        </bk-pop-confirm>
      )),
    },
    {
      label: t('流程预览'),
      field: 'flow_desc',
      showOverflowTooltip: true,
      width: 520,
      render: ({ data }: { data: RowData }) => <span>{data.flow_desc.join(' -> ')}</span>,
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
      render: ({ data }: { data: RowData }) => <span>{utcDisplayTime(data.update_at)}</span>,
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

  const handleCheckBoxValueChange = (row: RowData, key: string, checked: boolean) => {
    currentChoosedRow.value = row;
    currentFlow.value = key;
    // TODO: 组件有bug, 暂时先这样处理
    nextTick(() => {
      Object.assign(row.configs, {
        [key]: !checked,
      });
    });
  };

  const handleConfirmCheck = _.debounce((row: RowData) => {
    const { configs } = _.cloneDeep(row);
    Object.assign(configs, {
      [currentFlow.value]: !configs[currentFlow.value],
    });
    const params = {
      ticket_types: [row.ticket_type],
      configs,
    };
    runUpdateTicketFlowConfig(params);
  }, 500);

  const handleBatchEditSuccess = () => {
    fetchHostNodes();
  };

  const handleSelection = (data: RowData, list: RowData[]) => {
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
      background: #F0F1F5;
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
.ticket-flow-change-node-box {
  .item-box {
    display: flex;
    width: 100%;

    .title {
      width: 60px
    }

    .content {
      flex: 1;
      height: auto;

      .add-node {
        color: #FF9C01;
      }

      .delete-node {
        color: #EA3636;
        text-decoration:line-through;
      }
    }
  }
}
</style>
