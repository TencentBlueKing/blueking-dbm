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
      :title="t('重建从库_原机器或新机器重新同步数据及权限_并且将域名解析指向同步好的机器')" />
    <BkForm
      class="toolbox-form mb-20"
      form-type="vertical"
      :model="formData">
      <SlaveRestoreFormItem v-model="formData.restore_type" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <SlaveInstanceColumn
            v-model="item.slave"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.slave.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import SqlserverHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
  import type { Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import SlaveRestoreFormItem from '@views/db-manage/sqlserver/common/slave-restore-form-item/Index.vue';

  import { random } from '@utils';

  import SlaveInstanceColumn from './components/SlaveInstanceColumn.vue';

  interface RowData {
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      instance_address: string;
      ip: string;
      master_domain: string;
      port: number;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    slave: data.slave || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: '',
      ip: '',
      master_domain: '',
      port: 0,
    },
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    restore_type: TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE,
    tableData: [createTableRow()],
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2:2000',
      key: 'instance_address',
      label: t('目标从库实例'),
    },
  ];

  const tableKey = ref(random());
  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  useTicketDetail<Sqlserver.RestoreLocalSlave>(TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            slave: { instance_address: `${item.slave.ip}:${item.slave.port}` } as RowData['slave'],
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      };
    }[];
  }>(TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            cluster_id: item.slave.cluster_id,
            slave: {
              bk_biz_id: item.slave.bk_biz_id,
              bk_cloud_id: item.slave.bk_cloud_id,
              bk_host_id: item.slave.bk_host_id,
              ip: item.slave.ip,
              port: item.slave.port,
            },
          })),
        },
        ...formData.payload,
      });
    }
  };

  const handleBatchEdit = (list: SqlserverHaInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            slave: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              instance_address: item.instance_address,
              ip: item.ip,
              master_domain: item.master_domain,
              port: item.port,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          slave: { instance_address: item.instance_address } as RowData['slave'],
        }),
      );
      return acc;
    }, []);

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
