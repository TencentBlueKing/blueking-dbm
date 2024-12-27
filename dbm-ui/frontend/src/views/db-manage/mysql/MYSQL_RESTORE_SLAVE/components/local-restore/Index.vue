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
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <SlaveInstanceColumnGroup
            v-model="item.slave"
            :selected="selected"
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

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import BackupSource from '@views/db-manage/common/toolbox-field/backup-source/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/ticket-remark/Index.vue';

  import SlaveInstanceColumnGroup, { type SelectorHost } from './SlaveInstanceColumnGroup.vue';

  interface RowData {
    slave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      instance_address: string;
      cluster_id: number;
      master_domain: string;
    };
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    slave: Object.assign({}, data.slave),
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    backupSource: BackupSourceType.REMOTE,
    remark: '',
  });

  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  const rules = {
    'slave.instance': [
      {
        validator: (value: string) => selected.value.filter((item) => item.instance_address === value).length < 2,
        message: t('目标实例重复'),
        trigger: 'change',
      },
    ],
  };

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_id: number;
      slave: {
        bk_biz_id: number;
        bk_host_id: number;
        bk_cloud_id: number;
        ip: string;
        port: number;
      };
    }[];
  }>(TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, {
    onSuccess(ticketId) {
      router.push({
        name: TicketTypes.MYSQL_RESTORE_SLAVE, // 以新机重建单据为主路由
        params: {
          page: 'success',
        },
        query: {
          ticketId,
        },
      });
    },
  });

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun(
        {
          backup_source: formData.backupSource,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.slave.cluster_id,
            slave: {
              bk_biz_id: item.slave.bk_biz_id,
              bk_host_id: item.slave.bk_host_id,
              bk_cloud_id: item.slave.bk_cloud_id,
              ip: item.slave.ip,
              port: item.slave.port,
            },
          })),
        },
        formData.remark,
      );
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            slave: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              port: item.port,
              instance_address: item.instance_address,
              cluster_id: item.cluster_id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
