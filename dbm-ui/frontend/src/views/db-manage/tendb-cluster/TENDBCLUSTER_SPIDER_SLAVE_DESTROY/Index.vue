<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
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
      :title="
        t(
          '批量下架集群的只读接入层（Spider Slave 实例）。只读接入层为业务提供只读域名访问入口，常用于读写分离与读流量分担；下架后业务将无法通过只读域名访问数据，主集群读写访问不受影响。',
        )
      " />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <DbForm
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
            allow-repeat
            :disable-rule="disableRule"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <EditableColumn
            :label="t('Spider Slave 实例')"
            :min-width="200"
            readonly>
            <EditableBlock v-if="item.cluster.id">
              <template v-if="item.cluster.spider_slave.length > 0">
                <p
                  v-for="(slave, idx) of item.cluster.spider_slave"
                  :key="slave?.bk_instance_id || idx">
                  {{ slave?.instance || '--' }}
                </p>
              </template>
              <template v-else> -- </template>
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
      <TicketPayload v-model="formData.payload" />
    </DbForm>
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
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: TendbClusterModel;
  }

  const { t } = useI18n();
  const router = useRouter();

  // 无只读接入层（spider_slave.length === 0）的集群将被禁选并在表格中拦截
  const disableRule = {
    handler: (data: TendbClusterModel) => data.spider_slave?.length === 0,
    tip: t('该集群无只读接入层'),
  };

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbcluster.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
  ];

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
        spider_slave: [] as TendbClusterModel['spider_slave'],
      } as TendbClusterModel,
      data.cluster,
    ),
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  useTicketDetail<TendbCluster.SpiderSlaveDestroy>(TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_DESTROY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.cluster_ids.map((id: number) => ({
          cluster: {
            master_domain: details.clusters[id]?.immute_domain || '',
          },
        })),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    cluster_ids: number[];
    is_safe: boolean;
  }>(TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_DESTROY);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }

    createTicketRun({
      details: {
        cluster_ids: formData.tableData.map((item) => item.cluster.id),
        is_safe: true,
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: cluster.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    const newData = [...(formData.tableData[0]?.cluster?.id ? formData.tableData : []), ...dataList] as any;
    formData.tableData.splice(0, formData.tableData.length, ...newData);
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        cluster: {
          master_domain: item.master_domain,
        } as TendbClusterModel,
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
