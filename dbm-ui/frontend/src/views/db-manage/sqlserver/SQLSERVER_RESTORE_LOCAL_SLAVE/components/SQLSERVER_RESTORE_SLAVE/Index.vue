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
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <SlaveHostColumnGroup
            v-model="item.slave"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SingleResourceHostColumn
            v-model="item.newSlave"
            field="newSlave.ip"
            :label="t('新从库主机')"
            :params="{
              for_bizs: [currentBizId, 0],
              os_names: item.slave.system_version.split(','),
              resource_types: [DBTypes.SQLSERVER, 'PUBLIC'],
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
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import SlaveHostColumnGroup, { type SelectorHost } from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    newSlave: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    slave: {
      bk_cloud_id: number;
      bk_host_id: number;
      db_module_id: number;
      ip: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
      system_version: string;
    };
  }

  interface Props {
    ticketDetails?: TicketModel<Sqlserver.ResourcePool.RestoreSlave>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data = {} as Partial<RowData>) => ({
    newSlave: data.newSlave || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
    slave: data.slave || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      db_module_id: 0,
      ip: '',
      related_clusters: [],
      system_version: '',
    },
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

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
          hosts: {
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.SQLSERVER_RESTORE_SLAVE);

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails.details;
        Object.assign(formData, {
          ...createTickePayload(props.ticketDetails),
        });
        if (infos.length > 0) {
          formData.tableData = infos.map((item) =>
            createTableRow({
              newSlave: item.resource_spec.sqlserver_ha.hosts[0],
              slave: {
                ...item.old_nodes.old_slave_host[0],
                db_module_id: clusters[item.cluster_ids[0]].db_module_id,
                related_clusters: item.cluster_ids.map((id) => ({
                  id: id,
                  master_domain: clusters[id].immute_domain,
                })),
                system_version: '',
              },
            }),
          );
        }
      }
    },
  );

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
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
                hosts: [item.newSlave],
                spec_id: 0,
              },
            },
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            slave: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              db_module_id: item.db_module_id,
              ip: item.ip,
              related_clusters: item.related_clusters.map((cluster) => ({
                id: cluster.id,
                master_domain: cluster.master_domain,
              })),
              system_version: '',
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
