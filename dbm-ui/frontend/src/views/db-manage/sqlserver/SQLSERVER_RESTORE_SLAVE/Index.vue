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
      class="toolbox-form mt-16 mb-20"
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
          <SlaveHostColumnGroup
            v-model="item.slave"
            :selected="selected"
            @batch-edit="handleBatchEditSlave" />
          <!-- <SingleResourceHostColumn
            v-model="item.newSlave"
            field="newSlave.ip"
            :label="t('新从库主机')"
            :params="{
              for_bizs: [currentBizId, 0],
              os_names: item.slave.system_version.split(','),
              resource_types: [DBTypes.SQLSERVER, 'PUBLIC'],
            }" /> -->
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.SQLSERVER"
            :current-spec-id-list="[item.slave.spec_config.id]"
            :machine-type="MachineTypes.SQLSERVER"
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.slave.related_clusters?.[0]?.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.SQLSERVER, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import SqlserverMachineModel from '@services/model/sqlserver/sqlserver-machine';
  import { type Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  // import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import SlaveRestoreFormItem from '@views/db-manage/sqlserver/common/slave-restore-form-item/Index.vue';

  import { random } from '@utils';

  import SlaveHostColumnGroup from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    slave: {
      bk_cloud_id: number;
      bk_host_id: number;
      // db_module_id: number;
      ip: string;
      related_clusters: {
        id: number;
        master_domain: string;
        region: string;
      }[];
      spec_config: {
        id: number;
      };
      // system_version: string;
    };
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data = {} as Partial<RowData>) => ({
    labels: (data.labels || []) as RowData['labels'],
    slave: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        // db_module_id: 0,
        ip: '',
        related_clusters: [] as RowData['slave']['related_clusters'],
        // system_version: '',
        spec_config: {
          id: 0,
        },
      },
      data.slave,
    ),
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    restore_type: TicketTypes.SQLSERVER_RESTORE_SLAVE,
    tableData: [createTableRow()],
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标从库主机'),
    },
    {
      case: '2核_4G_50G',
      key: 'spec_name',
      label: t('目标规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const tableKey = ref(random());
  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Sqlserver.ResourcePool.RestoreSlave>(TicketTypes.SQLSERVER_RESTORE_SLAVE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            labels: (item.resource_spec.sqlserver_ha.labels || []).map((item) => ({ id: Number(item) })),
            slave: { ip: item.old_nodes.old_slave_host[0].ip } as RowData['slave'],
            specId: item.resource_spec.sqlserver_ha.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      old_nodes: {
        old_slave_host: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      resource_spec: {
        sqlserver_ha: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.SQLSERVER_RESTORE_SLAVE);

  const handleSubmit = () => {
    tableRef.value!.validate().then(() => {
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => ({
            cluster_ids: item.slave.related_clusters.map((item) => item.id),
            old_nodes: {
              old_slave_host: [
                {
                  bk_cloud_id: item.slave.bk_cloud_id,
                  bk_host_id: item.slave.bk_host_id,
                  ip: item.slave.ip,
                },
              ],
            },
            resource_spec: {
              sqlserver_ha: {
                count: 1,
                label_names: item.labels.map((item) => item.value),
                labels: item.labels.map((item) => String(item.id)),
                spec_id: item.specId,
              },
            },
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    });
  };

  const handleBatchEditSlave = (list: SqlserverMachineModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            slave: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              // db_module_id: item.db_module_id,
              ip: item.ip,
              related_clusters: item.related_clusters.map((cluster) => ({
                id: cluster.id,
                master_domain: cluster.immute_domain,
                region: cluster.region,
              })),
              spec_config: {
                id: item.spec_config.id,
              },
              // system_version: '',
            },
            specId: item.spec_config.id,
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
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          slave: { ip: item.ip } as RowData['slave'],
          specId: item.spec_name,
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

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
