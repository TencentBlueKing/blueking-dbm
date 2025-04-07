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
          <EditableColumn
            :label="t('同机关联集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.slave.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('当前资源规格')"
            :min-width="150">
            <EditableBlock
              v-model="item.slave.spec_name"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <NewSlaveHostColumn
            :slave="item.slave"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BackupSource v-model="formData.backupSource" />
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

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import NewSlaveHostColumn from './components/NewSlaveHostColumn.vue';
  import SlaveHostColumnGroup, { type SelectorHost } from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      master_domain: string;
      related_instances: string[];
      spec_id: number;
      spec_name: string;
    };
  }

  interface Props {
    ticketDetails?: TicketModel<TendbCluster.ResourcePool.RestoreSlave>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    slave: data.slave || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      count: 0,
      ip: '',
      master_domain: '',
      related_instances: [],
      spec_id: 0,
      spec_name: '',
    },
  });

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_id: number;
      old_nodes: {
        old_slave: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      resource_spec: {
        new_slave: {
          count: number;
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.TENDBCLUSTER_RESTORE_SLAVE);

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { backup_source: backupSource, infos } = props.ticketDetails.details;
        Object.assign(formData, {
          backupSource,
          ...createTickePayload(props.ticketDetails),
        });
        if (infos.length > 0) {
          formData.tableData = infos.map((item) =>
            createTableRow({
              slave: {
                ...item.old_nodes.old_slave[0],
                cluster_id: 0,
                master_domain: '',
                related_instances: [],
                spec_id: 0,
                spec_name: '',
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
          backup_source: formData.backupSource,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.slave.cluster_id,
            old_nodes: {
              old_slave: [
                {
                  bk_biz_id: item.slave.bk_biz_id,
                  bk_cloud_id: item.slave.bk_cloud_id,
                  bk_host_id: item.slave.bk_host_id,
                  ip: item.slave.ip,
                },
              ],
            },
            resource_spec: {
              new_slave: {
                count: 1,
                spec_id: item.slave.spec_id,
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
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              ip: item.ip,
              master_domain: item.master_domain,
              related_instances: item.related_instances.map((item) => item.instance),
              spec_id: item.spec_config?.id ?? 0,
              spec_name: item.spec_config?.name ?? '',
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
