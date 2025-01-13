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
  <SmartAction>
    <BkAlert
      class="mb-20"
      closable
      :title="t('主库故障切换：Slave 提升成主库，断开同步，切换后集群成单节点状态，一般用于紧急切换')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MasterHostColumn
            v-model="item.master"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SlaveHostColumn
            v-model="item.slave"
            :master="item.master" />
          <Column
            :label="t('所属集群')"
            :min-width="150">
            <Block
              v-model="item.cluster.master_domain"
              :placeholder="t('自动生成')" />
          </Column>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <CheckGroup
        v-model:is_check_delay="formData.is_check_delay"
        v-model:is_check_process="formData.is_check_process"
        v-model:is_verify_checksum="formData.is_verify_checksum" />
      <TicketRemark v-model="formData.remark" />
    </BkForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import CheckGroup from '@views/db-manage/common/toolbox-field/form-item/check-group/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import MasterHostColumn, { type SelectorHost } from './components/MasterHostColumn.vue';
  import SlaveHostColumn from './components/SlaveHostColumn.vue';

  interface RowData {
    master: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    slave: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    cluster: {
      id: number;
      master_domain: string;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    master: data.master || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
    slave: data.slave || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
    cluster: data.cluster || {
      id: 0,
      master_domain: '',
    },
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    is_check_process: true,
    is_verify_checksum: true,
    is_check_delay: true,
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() =>
    formData.tableData.filter((item) => item.master.bk_host_id).map((item) => item.master),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    is_check_process: boolean;
    is_verify_checksum: boolean;
    is_check_delay: boolean;
    infos: {
      cluster_id: number;
      switch_tuples: {
        master: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        };
        slave: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        };
      }[];
    }[];
  }>(TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        is_check_process: formData.is_check_process,
        is_verify_checksum: formData.is_verify_checksum,
        is_check_delay: formData.is_check_delay,
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          switch_tuples: [
            {
              master: item.master,
              slave: item.slave,
            },
          ],
        })),
      },
      remark: formData.remark,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            master: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
            },
            cluster: {
              id: item.cluster_id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
