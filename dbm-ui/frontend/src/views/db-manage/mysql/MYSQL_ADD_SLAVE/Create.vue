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
  <SmartAction class="mysql-add-slave">
    <BkAlert
      class="mb-20"
      closable
      :title="t('添加从库_同机的所有集群会统一新增从库_但新机器不添加到域名解析中去')" />
    <EditableTable
      ref="table"
      class="mb-20"
      :model="formData.tableData"
      :rules="rules">
      <EditableTableRow
        v-for="(item, index) in formData.tableData"
        :key="index">
        <RenderCluster
          v-model="item.cluster"
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <RenderHost v-model="item.slave" />
        <OperationColumn
          v-model:table-data="formData.tableData"
          :create-row-method="createData" />
      </EditableTableRow>
    </EditableTable>
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <BkFormItem
        :label="t('备份源')"
        property="backupSource"
        required>
        <BkRadioGroup v-model="formData.backupSource">
          <BkRadio label="local">
            {{ t('本地备份') }}
          </BkRadio>
          <BkRadio label="remote">
            {{ t('远程备份') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
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

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';

  import RenderCluster from './components/RenderCluster.vue';
  import RenderHost from './components/RenderHost.vue';

  interface RowData {
    cluster: {
      id: number;
      domain: string;
      relatedClusters: {
        id: number;
        domain: string;
      }[];
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

  const createData = (data = {} as Partial<RowData>) => ({
    cluster: Object.assign({}, data.cluster),
    slave: Object.assign({}, data.slave),
  });

  const formData = reactive({
    backupSource: 'local' as 'local' | 'remote',
    tableData: [createData()],
  });
  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const clusterMemo = computed(() => Object.fromEntries(selected.value.map((item) => [item.domain, true])));

  const rules = {
    'cluster.domain': [
      {
        validator: (value: string) => Boolean(clusterMemo.value[value]),
        message: t('目标集群重复'),
        trigger: 'blur',
      },
    ],
  };

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    backup_source: 'local' | 'remote';
    infos: {
      cluster_ids: number[];
      new_slave: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
      };
    }[];
  }>(TicketTypes.MYSQL_ADD_SLAVE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      backup_source: formData.backupSource,
      infos: formData.tableData.map((item) => ({
        cluster_ids: [item.cluster.id, ...item.cluster.relatedClusters.map((item) => item.id)],
        new_slave: item.slave,
      })),
    });
  };

  const handleReset = () => {
    formData.tableData = [createData()];
    formData.backupSource = 'local';
  };

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!clusterMemo.value[item.master_domain]) {
        acc.push(
          createData({
            cluster: {
              id: item.id,
              domain: item.master_domain,
              relatedClusters: [],
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
