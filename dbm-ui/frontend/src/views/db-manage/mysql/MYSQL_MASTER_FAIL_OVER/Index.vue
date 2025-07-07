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
      :title="t('Slave提升成主库_断开同步_切换后集成成单点状态_一般用于紧急切换')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MasterHostColumn
            v-model="item.master"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SlaveHostColumn
            v-model="item.slave"
            :master-host="item.master" />
          <EditableColumn
            :label="t('同机关联的集群')"
            :min-width="150"
            required>
            <EditableBlock v-if="item.master.related_clusters.length">
              <p
                v-for="cluster in item.master.related_clusters"
                :key="cluster.id">
                {{ cluster.master_domain }}
              </p>
            </EditableBlock>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem class="mb-8">
        <BkCheckbox v-model="formData.is_check_process">
          {{ t('检查业务来源的连接') }}
        </BkCheckbox>
      </BkFormItem>
      <BkFormItem class="mb-8">
        <BkCheckbox v-model="formData.is_verify_checksum">
          {{ t('检查主从同步延迟') }}
        </BkCheckbox>
      </BkFormItem>
      <BkFormItem class="mb-8">
        <BkCheckbox v-model="formData.is_check_delay">
          {{ t('检查主从数据校验结果') }}
        </BkCheckbox>
      </BkFormItem>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import type { _DeepPartial } from 'pinia';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import MasterHostColumn, { type SelectorHost } from './components/MasterHostColumn.vue';
  import SlaveHostColumn from './components/SlaveHostColumn.vue';

  interface RowData {
    master: ComponentProps<typeof MasterHostColumn>['modelValue'];
    slave: ComponentProps<typeof SlaveHostColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主库主机'),
    },
  ];

  const createTableRow = (data: _DeepPartial<RowData> = {}) => ({
    master: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        related_clusters: [] as RowData['master']['related_clusters'],
        role: '',
      },
      data.master,
    ),
    slave: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.slave,
    ),
  });

  const defaultData = () => ({
    is_check_delay: false,
    is_check_process: false,
    is_verify_checksum: false,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.master.bk_host_id).map((item) => item.master),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mysql.MasterFailOver>(TicketTypes.MYSQL_MASTER_FAIL_OVER, {
    async onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        is_check_delay: details.is_check_delay,
        is_check_process: details.is_check_process,
        is_verify_checksum: details.is_verify_checksum,
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            master: {
              ip: item.master_ip.ip,
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      master_ip: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
      slave_ip: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }[];
    is_check_delay: boolean;
    is_check_process: boolean;
    is_verify_checksum: boolean;
  }>(TicketTypes.MYSQL_MASTER_FAIL_OVER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_ids: item.master.related_clusters.map((item) => item.id),
          master_ip: {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: item.master.bk_cloud_id,
            bk_host_id: item.master.bk_host_id,
            ip: item.master.ip,
          },
          slave_ip: {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: item.slave.bk_cloud_id,
            bk_host_id: item.slave.bk_host_id,
            ip: item.slave.ip,
          },
        })),
        is_check_delay: formData.is_check_delay,
        is_check_process: formData.is_check_process,
        is_verify_checksum: formData.is_verify_checksum,
      },
      ...formData.payload,
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
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        master: {
          ip: item.ip,
        },
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };
</script>
