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
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('全库备份：所有库表备份, 除 MySQL 系统库和 DBA 专用库外')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16 toolbox-form"
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
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <BackupLocalColumn
            v-model="item.backup_local"
            :cluster="item.cluster"
            @batch-edit="handleBatchEdit" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem
        :label="t('备份类型')"
        property="backup_type"
        required>
        <BkRadioGroup v-model="formData.backup_type">
          <BkRadio label="logical">
            {{ t('逻辑备份') }}
          </BkRadio>
          <BkRadio label="physical">
            {{ t('物理备份') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('备份保存时间')"
        property="file_tag"
        required>
        <BkRadioGroup v-model="formData.file_tag">
          <BkRadio label="DBFILE1M">
            {{ t('1个月') }}
          </BkRadio>
          <BkRadio label="DBFILE6M">
            {{ t('6个月') }}
          </BkRadio>
          <BkRadio label="DBFILE1Y">
            {{ t('1年') }}
          </BkRadio>
          <BkRadio label="DBFILE3Y">
            {{ t('3年') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
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
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import BackupLocalColumn from './components/BackupLocalColumn.vue';

  interface RowData {
    backup_local: string;
    cluster: TendbclusterModel;
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'spider.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'RemoteDB',
      key: 'backup_local',
      label: t('备份位置'),
      values: ['RemoteDB', 'RemoteDR', '192.168.0.1:10000'],
    },
  ];

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    backup_local: data.backup_local || '',
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbclusterModel,
      data.cluster,
    ),
  });

  const defaultData = () => ({
    backup_type: 'logical',
    file_tag: 'DBFILE1M',
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.cluster.master_domain, true])),
  );

  useTicketDetail<TendbCluster.FullBackup>(TicketTypes.TENDBCLUSTER_FULL_BACKUP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        backup_type: details.backup_type,
        file_tag: details.file_tag,
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            backup_local: item.spider_mnt_address ? `spider_mnt::${item.spider_mnt_address}` : item.backup_local,
            cluster: {
              master_domain: clusters[item.cluster_id].immute_domain || '',
            },
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_type: string;
    file_tag: string;
    infos: {
      backup_local: string;
      cluster_id: number;
    }[];
  }>(TicketTypes.TENDBCLUSTER_FULL_BACKUP);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        backup_type: formData.backup_type,
        file_tag: formData.file_tag,
        infos: formData.tableData.map((item) => ({
          backup_local: item.backup_local,
          cluster_id: item.cluster.id,
        })),
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: TendbclusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            cluster,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        backup_local: item.backup_local || '',
        cluster: {
          master_domain: item.master_domain,
        } as TendbclusterModel,
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
  };
</script>
