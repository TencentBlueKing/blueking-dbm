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
        class="mb-20 proxy-rebuild-tip"
        closable
        theme="warning"
        :title="
          t(
            'Proxy 原地重建：在原主机上重建异常的 Proxy 进程（拓扑/IP/端口不变）。如整组 Proxy 不可用，请使用「Proxy 灾难重建」',
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
            v-model="item.originProxy"
            :handle-row-merge="handleRowMerge"
            :rowspan="item.rowspan"
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

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup from './components/HostColumnGroup.vue';

  interface RowData {
    originProxy: ComponentProps<typeof HostColumnGroup>['modelValue'];
    rowspan: number;
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2:10000',
      key: 'instance_address',
      label: t('实例'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    originProxy: Object.assign(
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
      } as RowData['originProxy'],
      data.originProxy,
    ),
    rowspan: data.rowspan || 1,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const tableKey = ref(random());
  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.originProxy.bk_host_id).map((item) => item.originProxy),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  // 按 cluster_id 聚合：同集群下的多个 Proxy 实例视觉合并 + 提交分组
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};

  const handleRowMerge = () => {
    const isResponsed = formData.tableData.every((item) => !!item.originProxy.cluster_id);
    if (!isResponsed) {
      return;
    }

    formData.tableData = [..._.sortBy(formData.tableData, (item) => item.originProxy.cluster_id)];

    sameClusterIdsRowsMap = {};
    formData.tableData.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const id = item.originProxy.cluster_id;
      if (!sameClusterIdsRowsMap[id]) {
        sameClusterIdsRowsMap[id] = [item];
      } else {
        sameClusterIdsRowsMap[id].push(item);
      }
    });
    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
    });
  };

  useTicketDetail<Mysql.ResourcePool.ProxyRebuild>(TicketTypes.MYSQL_PROXY_REBUILD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.reduce<RowData[]>((acc, item) => {
          item.rebuild_proxy_hosts?.forEach((host) => {
            acc.push(
              createTableRow({
                originProxy: {
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
    infos: Mysql.ResourcePool.ProxyRebuild['infos'];
    is_safe: boolean;
  }>(TicketTypes.MYSQL_PROXY_REBUILD);

  const handleBatchEdit = (list: TendbhaInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            originProxy: {
              instance_address: item.instance_address,
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
          originProxy: {
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
      // 按 cluster_id 分组生成 infos；每组 rebuild_proxy_hosts 列出该集群下所有目标 Proxy 主机
      createTicketRun({
        details: {
          infos: Object.values(sameClusterIdsRowsMap).map((rows) => ({
            cluster_id: rows[0].originProxy.cluster_id,
            rebuild_proxy_hosts: rows.map((row) => ({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: row.originProxy.bk_cloud_id,
              bk_host_id: row.originProxy.bk_host_id,
              ip: row.originProxy.ip,
              port: row.originProxy.port,
            })),
          })),
          is_safe: true,
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
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>

<style lang="less">
  .proxy-rebuild-tip.bk-alert {
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
