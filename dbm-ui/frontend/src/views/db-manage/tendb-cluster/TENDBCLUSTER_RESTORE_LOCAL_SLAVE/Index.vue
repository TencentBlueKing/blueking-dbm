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
    <div class="title-spot mt-12 mb-10">{{ t('重建类型') }}<span class="required" /></div>
    <div class="mt-8 mb-20">
      <CardCheckbox
        v-model="restoreType"
        :desc="t('在原主机上进行故障从库实例重建')"
        icon="rebuild"
        :title="t('原地重建')"
        :true-value="TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE" />
      <CardCheckbox
        v-model="restoreType"
        class="ml-8"
        :desc="t('将从库主机的全部实例重建到新主机')"
        icon="host"
        :title="t('新机重建')"
        :true-value="TicketTypes.TENDBCLUSTER_RESTORE_SLAVE" />
    </div>
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
          <SlaveInstanceColumn
            v-model="item.slave"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.slave.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { type TendbCluster } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import SlaveInstanceColumn, { type SelectorHost } from './components/SlaveInstanceColumn.vue';

  interface RowData {
    slave: ComponentProps<typeof SlaveInstanceColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const router = useRouter();

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    slave: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: '',
      ip: '',
      master_domain: '',
      port: 0,
      role: '',
      ...data.slave,
    },
  });

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const restoreType = ref<TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE | TicketTypes.TENDBCLUSTER_RESTORE_SLAVE>(
    TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
  );
  const formData = reactive(defaultData());
  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  useTicketDetail<TendbCluster.RestoreLocalSlave>(TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE, {
    onSuccess(ticketDetail) {
      const { backup_source: backupSource, infos } = ticketDetail.details;
      Object.assign(formData, {
        backupSource,
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            slave: {
              instance_address: `${item.slave.ip}:${item.slave.port}`,
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_id: number;
      slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
      };
    }[];
  }>(TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE);

  watch(restoreType, () => {
    if (restoreType.value === TicketTypes.TENDBCLUSTER_RESTORE_SLAVE) {
      router.push({
        name: TicketTypes.TENDBCLUSTER_RESTORE_SLAVE,
      });
    }
  });

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          backup_source: formData.backupSource,
          infos: formData.tableData.map((item) => ({
            cluster_id: item.slave.cluster_id,
            slave: {
              bk_biz_id: item.slave.bk_biz_id,
              bk_cloud_id: item.slave.bk_cloud_id,
              bk_host_id: item.slave.bk_host_id,
              ip: item.slave.ip,
              port: item.slave.port,
            },
          })),
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
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            slave: {
              instance_address: item.instance_address,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };
</script>
