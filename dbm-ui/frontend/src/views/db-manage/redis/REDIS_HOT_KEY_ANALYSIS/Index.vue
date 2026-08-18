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
      :title="t('对集群的实例进行热 Key 分析，热 Key 分析仅支持 TendisCache 、RedisCluster 、主从版。')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      ref="form"
      class="toolbox-form mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <InstanceColumn
            v-model="item.instance"
            :selected="selected"
            @batch-edit="handleInstanceBatchEdit" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.instance.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('架构版本')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.instance.cluster_type_name"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem
        :label="t('分析时长')"
        property="analysis_time"
        required>
        <BkSelect
          v-model="formData.analysis_time"
          :clearable="false"
          :list="timeSelectList"
          style="width: 300px" />
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import InstanceColumn from '@views/db-manage/redis/common/toolbox-field/instance-column/Index.vue';

  import { random } from '@utils';

  interface RowData {
    instance: NonNullable<ComponentProps<typeof InstanceColumn>['modelValue']>;
  }

  const { t } = useI18n();

  const batchInputConfig = [
    {
      case: '192.168.1.200:10000',
      key: 'instance',
      label: t('目标实例'),
    },
  ];

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('table');

  useTicketDetail<Redis.HotKeyAnalyse>(TicketTypes.REDIS_HOT_KEY_ANALYSIS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;
      Object.assign(formData, {
        analysis_time: details.analysis_time,
        payload: createTicketPayload(ticketDetail),
        tableData: infos.flatMap((item) =>
          item.ins.map((instanceItem) =>
            createTableRow({
              instance: {
                instance_address: instanceItem,
              } as RowData['instance'],
            }),
          ),
        ),
      });
    },
  });

  const createTableRow = (data = {} as Partial<RowData>) => ({
    instance: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_id: 0,
        cluster_type: '',
        cluster_type_name: '',
        instance_address: '',
        master_domain: '',
      },
      data.instance,
    ),
  });

  const defaultData = () => ({
    analysis_time: 10,
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const timeSelectList = [10, 30, 60].map((item) => ({
    label: `${item}s`,
    value: item,
  }));

  const tableKey = ref(random());

  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.instance.bk_host_id).map((item) => item.instance),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    analysis_time: number;
    bk_cloud_id: number;
    infos: {
      cluster_id: number;
      cluster_type: string;
      immute_domain: string;
      ins: string[];
    }[];
  }>(TicketTypes.REDIS_HOT_KEY_ANALYSIS);

  const handleInstanceBatchEdit = (list: RedisInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            instance: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              instance_address: item.instance_address,
              master_domain: item.master_domain,
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
        instance: {
          instance_address: item.instance,
        } as RowData['instance'],
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }

    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleSubmit = async () => {
    const result = await editableTableRef.value!.validate();
    if (!result) {
      return;
    }

    formRef.value!.validate().then(() => {
      const clusterMap = formData.tableData.reduce<Record<number, Redis.HotKeyAnalyse['infos'][number]>>(
        (prev, item) => {
          if (prev[item.instance.cluster_id]) {
            return Object.assign(prev, {
              [item.instance.cluster_id]: {
                ...prev[item.instance.cluster_id],
                ins: prev[item.instance.cluster_id].ins.concat(item.instance.instance_address),
              },
            });
          }
          return Object.assign(prev, {
            [item.instance.cluster_id]: {
              cluster_id: item.instance.cluster_id,
              cluster_type: item.instance.cluster_type,
              immute_domain: item.instance.master_domain,
              ins: [item.instance.instance_address],
            },
          });
        },
        {},
      );

      createTicketRun({
        details: {
          analysis_time: formData.analysis_time,
          bk_cloud_id: formData.tableData[0].instance.bk_cloud_id,
          infos: Object.values(clusterMap),
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
