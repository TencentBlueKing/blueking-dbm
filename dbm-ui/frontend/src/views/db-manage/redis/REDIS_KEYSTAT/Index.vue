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
      :title="t('对集群的实例进行内存分析，内存分析仅支持 TendisCache 、RedisCluster 、主从版。')" />
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
          v-for="item in formData.tableData"
          :key="item.row_key">
          <InstanceColumn
            v-model="item.instance"
            :data-source-map="dataSourceMap"
            :selected="selected"
            @batch-edit="handleInstanceBatchEdit" />
          <EditableColumn
            id-mark="master_domain"
            :label="t('所属集群')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.instance.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            id-mark="cluster_type_name"
            :label="t('架构版本')"
            :min-width="150"
            readonly>
            <EditableBlock
              v-model="item.instance.cluster_type_name"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <StatInfoColumnGroup
            v-model="item.stat_info"
            :instance="item.instance.instance_address" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
    <template #action>
      <BkButton
        v-test="{ type: 'button', value: 'submitTicket' }"
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

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import type { Redis } from '@services/model/ticket/ticket';
  import { getRedisInstances } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import InstanceColumn from '@views/db-manage/redis/common/toolbox-field/instance-column/Index.vue';

  import { random } from '@utils';

  import StatInfoColumnGroup from './components/StatInfoColumnGroup.vue';

  interface IRowData {
    instance: NonNullable<ComponentProps<typeof InstanceColumn>['modelValue']>;
    stat_info: ComponentProps<typeof StatInfoColumnGroup>['modelValue'];
  }

  const { t } = useI18n();

  const batchInputConfig = [
    {
      case: '192.168.1.200:10000',
      key: 'instance',
      label: t('目标实例'),
    },
  ];

  const dataSourceMap = {
    [ClusterTypes.REDIS]: (params: ServiceParameters<typeof getRedisInstances>) =>
      getRedisInstances({
        ...params,
        cluster_type: [
          ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
          ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ClusterTypes.REDIS_INSTANCE,
        ].join(','),
        role: 'redis_master',
      }),
  };

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('table');

  useTicketDetail<Redis.KeyStat>(TicketTypes.REDIS_KEYSTAT, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.flatMap((item) =>
          item.ins.map((instanceItem) =>
            createTableRow({
              instance: {
                instance_address: instanceItem.addr,
              } as IRowData['instance'],
            }),
          ),
        ),
      });
    },
  });

  const createTableRow = (data = {} as Partial<IRowData>) => ({
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
    row_key: random(),
    stat_info: {
      key_num: 0,
      memory_total: 0,
    },
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const tableKey = ref(random());

  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.instance.bk_host_id).map((item) => item.instance),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    bk_cloud_id: number;
    infos: Redis.KeyStat['infos'];
  }>(TicketTypes.REDIS_KEYSTAT, {
    onError(errors) {
      editableTableRef.value!.viewError(errors);
    },
  });

  const handleInstanceBatchEdit = (list: RedisInstanceModel[]) => {
    const dataList = list.reduce<ReturnType<typeof createTableRow>[]>((acc, item) => {
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
        } as IRowData['instance'],
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
      const clusterMap = formData.tableData.reduce<Record<number, Redis.KeyStat['infos'][number]>>((prev, item) => {
        const insItem = {
          addr: item.instance.instance_address,
          key_num: item.stat_info.key_num,
          memory_total: item.stat_info.memory_total,
        };
        if (prev[item.instance.cluster_id]) {
          return Object.assign(prev, {
            [item.instance.cluster_id]: {
              ...prev[item.instance.cluster_id],
              ins: prev[item.instance.cluster_id].ins.concat(insItem),
            },
          });
        }
        return Object.assign(prev, {
          [item.instance.cluster_id]: {
            cluster_id: item.instance.cluster_id,
            cluster_type: item.instance.cluster_type,
            immute_domain: item.instance.master_domain,
            ins: [insItem],
          },
        });
      }, {});

      createTicketRun({
        details: {
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
