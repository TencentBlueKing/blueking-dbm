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
      class="mb-16"
      closable
      :title="t('缩容接入层：减加集群的Proxy数量，但集群Proxy数量不能少于2')" />
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
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('缩容节点类型')"
            readonly
            :width="180">
            <EditableBlock v-model="item.role" />
          </EditableColumn>
          <!-- <EditableColumn
            :label="t('当前规格')"
            :min-width="180">
            <EditableBlock v-if="item.cluster.spec_config.id">
              {{ item.cluster.spec_config.name }}
              <SpecDetailPopover
                v-if="item.cluster.spec_config.id"
                :data="item.cluster.spec_config">
                <DbIcon
                  class="visible-icon ml-4"
                  type="visible1" />
              </SpecDetailPopover>
            </EditableBlock>
            <EditableBlock
              v-else
              :placeholder="t('自动生成')" />
          </EditableColumn> -->
          <SpecColumn
            v-model="item.cluster.spec_config.id"
            :cluster-type="DBTypes.MONGODB"
            field="cluster.spec_config.id"
            :machine-type="MachineTypes.MONGOS"
            required />
          <IpColumn
            v-model="item.hosts"
            :cluster="item.cluster" />
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MongoDBModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  // import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import ClusterColumn from './components/ClusterColumn.vue';
  import IpColumn from './components/IpColumn.vue';

  interface RowData {
    cluster: {
      bk_cloud_id: number;
      id: number;
      master_domain: string;
      mongos: MongoDBModel['mongos'];
      spec_config: MongoDBModel['mongos'][0]['spec_config'];
    };
    hosts: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    role: 'mongos';
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        id: 0,
        master_domain: '',
        mongos: [] as MongoDBModel['mongos'],
        spec_config: {
          id: 0,
        } as MongoDBModel['mongos'][0]['spec_config'],
      },
      data.cluster,
    ),
    hosts: data.hosts || ([] as RowData['hosts']),
    role: data.role || 'mongos',
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('集群域名'),
    },
    {
      case: '192.168.10.2,192.168.10.3',
      key: 'hosts',
      label: t('缩容的 IP'),
    },
  ];

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<Mongodb.ResourcePool.ReduceMongos>(TicketTypes.MONGODB_REDUCE_MONGOS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((item) => {
          const clusterInfo = clusters[item.cluster_id];
          return createTableRow({
            cluster: {
              bk_cloud_id: clusterInfo.bk_cloud_id,
              id: clusterInfo.id,
              master_domain: clusterInfo.immute_domain,
              mongos: [] as MongoDBModel['mongos'],
              spec_config: {} as MongoDBModel['mongos'][0]['spec_config'],
            },
            hosts: item.old_nodes.mongos,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      old_nodes: {
        mongos: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      role: 'mongos';
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MONGODB_REDUCE_MONGOS);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_id: item.cluster.id,
          old_nodes: {
            mongos: item.hosts,
          },
          role: 'mongos',
        })),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        cluster: {
          master_domain: item.domain,
        } as RowData['cluster'],
        hosts: (item?.hosts || '').split(',').map((hostItem: string) => ({
          ip: hostItem,
        })),
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
  };

  const handleBatchEdit = (list: MongoDBModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              id: item.id,
              master_domain: item.master_domain,
              mongos: item.mongos,
              spec_config: item.mongos[0].spec_config,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
<style lang="less" scoped>
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
