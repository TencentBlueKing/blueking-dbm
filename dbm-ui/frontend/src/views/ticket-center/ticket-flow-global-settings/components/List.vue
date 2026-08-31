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
      <DbQuickSearch
        v-model="searchValue"
        class="input-box"
        :data="searchSelectList"
        :placeholder="t('请选择条件搜索')" />
    </div>
    <DbTable
      ref="tableRef"
      class="table-box"
      :data-source="queryTicketFlowDescribe"
      row-key="id"
      selectable
      @clear-search="handleClearSearch"
      @selection="handleSelection">
      <TableColumn
        col-key="ticket_type_display"
        :title="t('单据类型')"
        :width="220">
      </TableColumn>
      <TableColumn
        col-key="bk_biz_id"
        :title="t('目标')"
        :width="180">
        <template #default>
          {{ t('业务下全部对象') }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="need_itsm"
        :width="120">
        <template #title>
          <p
            v-bk-tooltips="t('是否经由DBA审批后才可执行')"
            class="configs-head">
            {{ t('是否审批') }}
          </p>
        </template>
        <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
          <RenderFlowPreview
            v-model="data.configs.need_itsm"
            config-key="need_itsm"
            :data="data"
            @success="fetchData">
            <AuthTemplate
              action-id="ticket_config_set"
              class="flow-node-action"
              :permission="data.permission.ticket_config_set"
              :resource="dbType">
              <BkCheckbox
                v-model="data.configs.need_itsm"
                style="pointer-events: none" />
            </AuthTemplate>
          </RenderFlowPreview>
        </template>
      </TableColumn>
      <TableColumn
        col-key="need_manual_confirm"
        :width="120">
        <template #title>
          <p
            v-bk-tooltips="t('是否经由提单人确认后才可执行')"
            class="configs-head">
            {{ t('是否人工确认') }}
          </p>
        </template>
        <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
          <RenderFlowPreview
            v-model="data.configs.need_manual_confirm"
            config-key="need_manual_confirm"
            :data="data"
            @success="fetchData">
            <AuthTemplate
              action-id="ticket_config_set"
              class="flow-node-action"
              :permission="data.permission.ticket_config_set"
              :resource="dbType">
              <BkCheckbox
                v-model="data.configs.need_manual_confirm"
                style="pointer-events: none" />
            </AuthTemplate>
          </RenderFlowPreview>
        </template>
      </TableColumn>
      <TableColumn
        col-key="flow_desc"
        ellipsis
        :title="t('流程预览')"
        :width="520">
        <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
          <span>{{ data.flow_desc.join(' -> ') }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="updater"
        ellipsis
        :title="t('更新人')"
        :width="120">
      </TableColumn>
      <TableColumn
        col-key="update_at"
        ellipsis
        sorter
        :title="t('更新时间')"
        :width="180">
        <template #default="{ row: data }: { row: TicketFlowDescribeModel }">
          {{ data.updateAtDisplay }}
        </template>
      </TableColumn>
    </DbTable>
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

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import BatchConfigDialog from './BatchConfigDialog.vue';
  import RenderFlowPreview from './RenderFlowPreview.vue';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();
  const isShowBatchConfigDialog = ref(false);
  const searchValue = ref<Record<string, string>>({});
  const ticketTypeList = shallowRef<{ label: string; value: string }[]>([]);
  const selected = shallowRef<TicketFlowDescribeModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selecedTicketTypes = computed(() => selected.value.map((item) => item.ticket_type));
  const searchSelectList = computed<QuickSearchProps['data']>(() => [
    {
      id: 'ticket_types',
      list: ticketTypeList.value,
      name: t('单据类型'),
      type: 'multiple',
    },
  ]);

  useRequest(getTicketTypes, {
    onSuccess: (data) => {
      ticketTypeList.value = data.map((item) => ({
        label: item.value,
        value: item.key,
      }));
    },
  });

  watch(searchValue, () => {
    fetchData();
  });

  watch(
    () => props.dbType,
    (type) => {
      if (type) {
        searchValue.value = {};
      }
    },
  );

  // watch(searchValue, () => {
  //   tableRef.value!.clearSelected();
  // });

  const fetchData = () => {
    tableRef.value.fetchData({
      // 全局配置下单据流程列表不传bk_biz_id,覆盖db-table组件传入的bk_biz_id,请求时会过滤掉值为undefined的字段
      bk_biz_id: undefined,
      db_type: props.dbType,
      ...searchValue.value,
    });
  };

  const handleSelection = (idList: string[], list: TicketFlowDescribeModel[]) => {
    selected.value = list;
  };

  const handleBatchEdit = () => {
    isShowBatchConfigDialog.value = true;
  };

  const handleClearSearch = () => {
    searchValue.value = {};
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
