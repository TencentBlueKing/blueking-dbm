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
    <div class="mb-16">
      <div class="title-spot mt-12 mb-10">{{ t('切换类型') }}<span class="required" /></div>
      <CardCheckbox
        v-model="operaObjectType"
        :desc="t('用于强制执行主机级别切换')"
        icon="host"
        :title="t('主机切换')"
        :true-value="OperaObejctType.MACHINE" />
      <CardCheckbox
        v-model="operaObjectType"
        class="ml-8"
        :desc="t('用于强制执行实例级别切换')"
        icon="rebuild"
        :title="t('实例切换')"
        :true-value="OperaObejctType.INSTANCE" />
      <BkAlert
        class="mt-10"
        theme="warning"
        :title="t('实例切换仅用于主机发生了【部分切换】后的修复场景，请谨慎操作！')" />
    </div>
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-16"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MasterColumn
            v-model="item.master"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SlaveColumn
            v-model="item.slave"
            :master="item.master" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150"
            required>
            <EditableBlock
              v-model="item.master.master_domain"
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';
  import { OperaObejctType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import MasterColumn, { type SelectorHost } from './components/MasterColumn.vue';
  import SlaveColumn from './components/SlaveColumn.vue';

  interface RowData {
    master: ComponentProps<typeof MasterColumn>['modelValue'];
    slave: ComponentProps<typeof SlaveColumn>['modelValue'];
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2:2000',
      key: 'instance_address',
      label: t('故障主库实例'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    master: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_id: 0,
        instance_address: '',
        ip: '',
        master_domain: '',
        port: 0,
        role: '',
      },
      data.master,
    ),
    slave: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        instance_address: '',
        ip: '',
        port: 0,
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

  const operaObjectType = ref(OperaObejctType.INSTANCE);
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.master.bk_host_id).map((item) => item.master),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  watch(operaObjectType, () => {
    if (operaObjectType.value === OperaObejctType.MACHINE) {
      router.push({
        name: TicketTypes.MYSQL_MASTER_FAIL_OVER,
      });
    }
  });

  useTicketDetail<Mysql.InstanceFailOver>(TicketTypes.MYSQL_INSTANCE_FAIL_OVER, {
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
              instance_address: `${item.master_ip.ip}:${item.master_ip.port}`,
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
        port: number;
      };
      slave_ip: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      };
    }[];
    is_check_delay: boolean;
    is_check_process: boolean;
    is_verify_checksum: boolean;
  }>(TicketTypes.MYSQL_INSTANCE_FAIL_OVER);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_ids: [item.master.cluster_id],
          master_ip: item.master,
          slave_ip: item.slave,
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
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            master: {
              instance_address: item.instance_address,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].master.bk_host_id ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          master: {
            instance_address: item.instance_address,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].master.bk_host_id ? formData.tableData : []), ...dataList];
    }
  };
</script>
