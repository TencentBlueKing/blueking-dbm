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
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <SlaveHostColumnGroup
            v-model="item.slave"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <Column
            :label="t('同机关联集群')"
            :min-width="150">
            <Block
              v-model="item.slave.master_domain"
              :placeholder="t('自动生成')" />
          </Column>
          <Column
            :label="t('当前资源规格')"
            :min-width="150">
            <Block
              v-model="item.slave.spec_name"
              :placeholder="t('自动生成')" />
          </Column>
          <NewSlaveHostColumn
            v-model="item.newSlave"
            :slave="item.slave"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <BackupSource v-model="formData.backupSource" />
      <TicketRemark v-model="formData.remark" />
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

  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';

  import NewSlaveHostColumn from './NewSlaveHostColumn.vue';
  import SlaveHostColumnGroup, { type SelectorHost } from './SlaveHostColumnGroup.vue';

  interface RowData {
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      related_instances: string[];
      cluster_id: number;
      master_domain: string;
      spec_id: number;
      spec_name: string;
      count: number;
    };
    newSlave: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    slave: data.slave || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      related_instances: [],
      cluster_id: 0,
      master_domain: '',
      spec_id: 0,
      spec_name: '',
      count: 0,
    },
    newSlave: 'resource_pool',
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    backupSource: BackupSourceType.REMOTE,
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    ip_source: 'resource_pool';
    backup_source: BackupSourceType;
    infos: {
      cluster_id: number;
      old_nodes: {
        old_slave: {
          bk_biz_id: number;
          bk_host_id: number;
          bk_cloud_id: number;
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
  }>(TicketTypes.TENDBCLUSTER_RESTORE_SLAVE);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          ip_source: 'resource_pool',
          backup_source: formData.backupSource,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.slave.cluster_id,
            old_nodes: {
              old_slave: [
                {
                  bk_biz_id: item.slave.bk_biz_id,
                  bk_host_id: item.slave.bk_host_id,
                  bk_cloud_id: item.slave.bk_cloud_id,
                  ip: item.slave.ip,
                },
              ],
            },
            resource_spec: {
              new_slave: {
                count: item.slave.count,
                spec_id: item.slave.spec_id,
              },
            },
          })),
        },
        remark: formData.remark,
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
              ip: item.ip,
              related_instances: item.related_instances.map((item) => item.instance),
              cluster_id: item.cluster_id,
              master_domain: item.master_domain,
              spec_id: item.spec_config?.id ?? 0,
              spec_name: item.spec_config?.name ?? '',
              count: item.spec_config?.count ?? 0,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
