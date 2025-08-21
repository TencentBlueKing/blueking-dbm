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
  <Teleport to="#dbContentTitleAppend">
    <BkTag
      class="ml-8"
      theme="info">
      {{ t('全局') }}
    </BkTag>
  </Teleport>
  <div class="ticket-flow-list-content">
    <BkAlert
      class="mb-16"
      closable>
      {{
        t(
          '全局设置的作为各个业务初始化设置，更改后会自动同步至各个业务；在业务下可以根据运行情况，可调整“是否审批”，其中“是否人工确认”在业务下不可更改',
        )
      }}
    </BkAlert>
    <div class="top-operation">
      <span
        v-bk-tooltips="{
          disabled: hasSelected,
          content: t('请选择单据'),
        }">
        <AuthButton
          action-id="ticket_config_set"
          :disabled="!hasSelected"
          :resource="dbType"
          theme="primary"
          @click="handleBatchEdit">
          {{ t('批量编辑') }}
        </AuthButton>
      </span>
      <BkSearchSelect
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList"
        :placeholder="t('请选择条件搜索')"
        unique-select
        value-split-code="+"
        @search="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      class="table-box"
      :columns="columns"
      :data-source="queryTicketFlowDescribe"
      primary-key="ticket_type"
      :row-config="{
        useKey: true,
        keyField: 'id',
      }"
      selectable
      @clear-search="handleClearSearch"
      @selection="handleSelection" />
  </div>
  <BatchConfigDialog
    v-model:is-show="isShowBatchConfigDialog"
    :ticket-types="selecedTicketTypes"
    @success="fetchData" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
  import { getTicketTypes, queryTicketFlowDescribe } from '@services/source/ticket';

  import type { DBTypes } from '@common/const';

  import BatchConfigDialog from './BatchConfigDialog.vue';
  import RenderFlowPreview from './RenderFlowPreview.vue';

  interface Props {
    dbType: DBTypes;
  }

  interface SearchSelectItem {
    id: string;
    name: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const isShowBatchConfigDialog = ref(false);
  const searchValue = ref<Array<{ values: SearchSelectItem[] } & SearchSelectItem>>([]);
  const ticketTypeList = shallowRef<SearchSelectItem[]>([]);
  const selected = shallowRef<TicketFlowDescribeModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selecedTicketTypes = computed(() => selected.value.map((item) => item.ticket_type));
  const reqParams = computed(() =>
    searchValue.value.reduce<Record<string, string>>((obj, item) => {
      Object.assign(obj, {
        [item.id]: item.values.map((data) => data.id).join(','),
      });
      return obj;
    }, {}),
  );
  const searchSelectList = computed(() => [
    {
      children: ticketTypeList.value,
      id: 'ticket_types',
      multiple: true,
      name: t('单据类型'),
    },
  ]);

  const columns = [
    {
      field: 'ticket_type_display',
      label: t('单据类型'),
      width: 220,
    },
    {
      field: 'bk_biz_id',
      label: t('目标'),
      render: () => t('业务下全部对象'),
      width: 180,
    },
    {
      field: 'need_itsm',
      label: t('是否审批'),
      render: ({ data }: { data: TicketFlowDescribeModel }) => (
        <RenderFlowPreview
          v-model={data.configs.need_itsm}
          configKey='need_itsm'
          data={data}
          onSuccess={fetchData}>
          <auth-template
            action-id='ticket_config_set'
            class='flow-node-action'
            permission={data.permission.ticket_config_set}
            resource={props.dbType}>
            <bk-checkbox
              v-model={data.configs.need_itsm}
              style='pointer-events: none'
            />
          </auth-template>
        </RenderFlowPreview>
      ),
      renderHead: () => (
        <p
          v-bk-tooltips={t('是否经由DBA审批后才可执行')}
          class='configs-head'>
          {t('是否审批')}
        </p>
      ),
      width: 120,
    },
    {
      field: 'need_manual_confirm',
      label: t('是否人工确认'),
      render: ({ data }: { data: TicketFlowDescribeModel }) => (
        <RenderFlowPreview
          v-model={data.configs.need_manual_confirm}
          configKey='need_manual_confirm'
          data={data}
          onSuccess={fetchData}>
          <auth-template
            action-id='ticket_config_set'
            class='flow-node-action'
            permission={data.permission.ticket_config_set}
            resource={props.dbType}>
            <bk-checkbox
              v-model={data.configs.need_manual_confirm}
              style='pointer-events: none'
            />
          </auth-template>
        </RenderFlowPreview>
      ),
      renderHead: () => (
        <p
          v-bk-tooltips={t('是否经由提单人确认后才可执行')}
          class='configs-head'>
          {t('是否人工确认')}
        </p>
      ),
      width: 120,
    },
    {
      field: 'flow_desc',
      label: t('流程预览'),
      render: ({ data }: { data: TicketFlowDescribeModel }) => <span>{data.flow_desc.join(' -> ')}</span>,
      showOverflowTooltip: true,
      width: 520,
    },
    {
      field: 'updater',
      label: t('更新人'),
      showOverflowTooltip: true,
      width: 120,
    },
    {
      field: 'update_at',
      label: t('更新时间'),
      render: ({ data }: { data: TicketFlowDescribeModel }) => data.updateAtDisplay,
      showOverflowTooltip: true,
      sort: true,
      width: 240,
    },
  ];

  useRequest(getTicketTypes, {
    onSuccess: (data) => {
      ticketTypeList.value = data.map((item) => ({
        id: item.key,
        name: item.value,
      }));
    },
  });

  watch(reqParams, () => {
    fetchData();
  });

  watch(
    () => props.dbType,
    (type) => {
      if (type) {
        searchValue.value = [];
      }
    },
  );

  watch(searchValue, () => {
    tableRef.value!.clearSelected();
  });

  const fetchData = () => {
    tableRef.value.fetchData(
      { ...reqParams.value },
      {
        // 全局配置下单据流程列表不传bk_biz_id,覆盖db-table组件传入的bk_biz_id,请求时会过滤掉值为undefined的字段
        bk_biz_id: undefined,
        db_type: props.dbType,
      },
    );
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

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less" scoped>
  .ticket-flow-list-content {
    display: flex;
    padding: 16px 24px;
    flex-direction: column;

    .top-operation {
      display: flex;
      width: 100%;
      height: 32px;
      justify-content: space-between;
      margin-bottom: 16px;

      .input-box {
        width: 600px;
      }
    }

    :deep(.table-box) {
      .configs-head {
        padding-bottom: 2px;
        border-bottom: 1px dashed #313238;
      }

      .flow-node-action {
        display: inline-block;
        cursor: pointer;

        & ~ .flow-node-action {
          margin-left: 24px;
        }
      }
    }
  }
</style>
