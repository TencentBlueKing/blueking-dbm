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
      :title="t('添加从库：同机的所有集群会统一新增从库，仅支持 always on 集群')" />
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.cluster"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SingleHost
            v-model="item.slave"
            field="slave.ip"
            :label="t('新从库主机')" />
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import BackupSource from '@views/db-manage/common/toolbox-field/backup-source/Index.vue';
  import SingleHost from '@views/db-manage/common/toolbox-field/host-column/SingleHost.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/ticket-remark/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    cluster: {
      id: number;
      domain: string;
    };
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: Object.assign({}, data.cluster),
    slave: Object.assign({}, data.slave),
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    backupSource: BackupSourceType.REMOTE,
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.domain, true])));

  const rules = {
    'cluster.domain': [
      {
        validator: (value: string) => selected.value.filter((item) => item.domain === value).length < 2,
        message: t('目标集群重复'),
        trigger: 'change',
      },
    ],
  };

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_ids: number[];
      resource_spec: {
        new_slave: {
          spec_id: number;
          count: number;
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
        };
      };
    }[];
  }>(TicketTypes.SQLSERVER_ADD_SLAVE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun(
      {
        backup_source: formData.backupSource,
        infos: formData.tableData.map((item) => ({
          cluster_ids: [item.cluster.id],
          resource_spec: {
            new_slave: {
              spec_id: 0,
              count: 1,
              hosts: [item.slave],
            },
          },
        })),
      },
      formData.remark,
    );
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SqlServerHaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              id: item.id,
              domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    nextTick(() => {
      tableRef.value!.validateByColumnIndex(0);
    });
  };
</script>
