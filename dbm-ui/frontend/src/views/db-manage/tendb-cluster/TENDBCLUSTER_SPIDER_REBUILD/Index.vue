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
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BkAlert
        class="mb-20 spider-rebuild-tip"
        closable
        theme="warning"
        :title="
          t(
            '接入层原地重建：在原主机上重建异常的 Spider 实例进程（拓扑/IP/端口不变）。如整组接入层不可用，请使用「接入层灾难重建」',
          )
        " />
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
          <HostColumnGroup
            v-model="item.originSpider"
            :handle-row-merge="handleRowMerge"
            :role-rowspan="item.same_role"
            :rowspan="item.same_cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow"
            :handle-row-merge="handleRowMerge" />
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
  import _ from 'lodash';
  import { computed, reactive, ref, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorHost } from './components/HostColumnGroup.vue';

  interface RowData {
    originSpider: ComponentProps<typeof HostColumnGroup>['modelValue'];
    same_cluster: number;
    same_role: number;
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2:25000',
      key: 'instance_address',
      label: t('实例'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    originSpider: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_id: 0,
        instance_address: '',
        ip: '',
        master_domain: '',
        port: 0,
        role: '',
        status: '',
      } as RowData['originSpider'],
      data.originSpider,
    ),
    same_cluster: data.same_cluster || 1,
    same_role: data.same_role || 1,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.originSpider.bk_host_id).map((item) => item.originSpider),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  // 双维度合并：cluster_id 维度（视觉），cluster_id+role 维度（提交分组）
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};
  let sameRoleRowsMap: Record<string, RowData[]> = {};

  const handleRowMerge = () => {
    const isResponsed = formData.tableData.every((item) => !!item.originSpider.cluster_id);
    if (!isResponsed) {
      return;
    }

    const sortedData = _.sortBy(formData.tableData, [
      (item) => item.originSpider.cluster_id,
      (item) => item.originSpider.role,
    ]);

    sameClusterIdsRowsMap = _.groupBy(sortedData, (item) => item.originSpider.cluster_id);
    sameRoleRowsMap = _.groupBy(sortedData, (item) => `${item.originSpider.cluster_id}-${item.originSpider.role}`);

    sortedData.forEach((item) => {
      Object.assign(item, { same_cluster: 1, same_role: 1 });
    });

    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      Object.assign(list[0], { same_cluster: list.length });
    });
    Object.values(sameRoleRowsMap).forEach((list) => {
      Object.assign(list[0], { same_role: list.length });
    });

    formData.tableData = sortedData;
  };

  useTicketDetail<TendbCluster.ResourcePool.SpiderRebuild>(TicketTypes.TENDBCLUSTER_SPIDER_REBUILD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.reduce<RowData[]>((acc, item) => {
          item.spider_ip_list?.forEach((host) => {
            acc.push(
              createTableRow({
                originSpider: {
                  instance_address: host.ip || '',
                },
              }),
            );
          });
          return acc;
        }, []),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: TendbCluster.ResourcePool.SpiderRebuild['infos'];
  }>(TicketTypes.TENDBCLUSTER_SPIDER_REBUILD);

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      // 选择器返回的是主机维度（IP），由用户在表格内补全 IP:Port
      const instanceAddress = item.instance_address || item.ip;
      if (!selectedMap.value[instanceAddress]) {
        acc.push(
          createTableRow({
            originSpider: {
              instance_address: instanceAddress,
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
          originSpider: {
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
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleSubmit = () => {
    tableRef.value!.validate().then(() => {
      // 按 cluster_id + role 双维度聚合：每个 (cluster, role) 生成一个 info 项
      const infos: TendbCluster.ResourcePool.SpiderRebuild['infos'] = Object.values(sameRoleRowsMap).map((rows) => ({
        cluster_id: rows[0].originSpider.cluster_id,
        rebuild_spider_role: rows[0].originSpider.role,
        spider_ip_list: rows.map((row) => ({
          bk_cloud_id: row.originSpider.bk_cloud_id,
          bk_host_id: row.originSpider.bk_host_id,
          ip: row.originSpider.ip,
          port: row.originSpider.port,
        })),
      }));

      createTicketRun({
        details: {
          infos,
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>

<style lang="less">
  .spider-rebuild-tip.bk-alert {
    background-color: #fff7e6;
    border: 1px solid #ffd591;

    .bk-alert-icon {
      color: #ff9c01;
    }

    .bk-alert-title {
      color: #63656e;
    }
  }
</style>
