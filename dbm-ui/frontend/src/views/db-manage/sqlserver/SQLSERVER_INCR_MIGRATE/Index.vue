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
      :title="t('数据迁移：数据同步复制到新集群，迁移后将会对原库进行')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('迁移类型')"
        required>
        <BkRadioGroup
          v-model="formData.ticketType"
          style="width: 400px"
          type="card"
          @change="handleMigrateTypeChange">
          <BkRadioButton :label="TicketTypes.SQLSERVER_FULL_MIGRATE">
            {{ t('一次性全备迁移') }}
          </BkRadioButton>
          <BkRadioButton :label="TicketTypes.SQLSERVER_INCR_MIGRATE">
            {{ t('持续增量迁移') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <SrcClusterColumn
            v-model="item.srcCluster"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <DstClusterColumn
            v-model="item.dstCluster"
            :selected-map="selectedMap"
            :src-cluster="item.srcCluster"
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.dbName"
            allow-asterisk
            check-not-exist
            :cluster-id="item.srcCluster.id"
            field="dbName"
            :label="t('迁移 DB 名')"
            required
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.dbIgnoreName"
            check-not-exist
            :cluster-id="item.srcCluster.id"
            field="dbIgnoreName"
            :label="t('忽略 DB 名')"
            :required="false"
            @batch-edit="handleBatchEdit" />
          <RenameColumn
            v-model="item.renameInfoList"
            v-model:db-ignore-name="item.dbIgnoreName"
            v-model:db-name="item.dbName"
            :data="item" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem
        class="mt-24"
        :label="t('DB名处理')">
        <BkRadioGroup v-model="formData.need_auto_rename">
          <BkRadio :label="false">
            {{ t('迁移后源DB继续使用，DB名不变') }}
          </BkRadio>
          <BkRadio label>
            {{ t('迁移后源DB不再使用，自动重命名') }}
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

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import type { Sqlserver } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';
  import DstClusterColumn from '@views/db-manage/sqlserver/SQLSERVER_FULL_MIGRATE/components/DstClusterColumn.vue';
  import RenameColumn from '@views/db-manage/sqlserver/SQLSERVER_FULL_MIGRATE/components/RenameColumn.vue';
  import SrcClusterColumn from '@views/db-manage/sqlserver/SQLSERVER_FULL_MIGRATE/components/SrcClusterColumn.vue';

  interface RowData {
    dbIgnoreName: string[];
    dbName: string[];
    dstCluster: {
      cluster_type: ClusterTypes;
      id: number;
      major_version: string;
      master_domain: string;
    }[];
    renameInfoList: {
      db_name: string;
      rename_cluster_list: number[];
      rename_db_name: string;
      target_db_name: string;
    }[];
    srcCluster: {
      cluster_type: ClusterTypes;
      id: number;
      major_version: string;
      master_domain: string;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const router = useRouter();

  const createTableRow = (data = {} as Partial<RowData>) => ({
    dbIgnoreName: data.dbIgnoreName || [],
    dbName: data.dbName || ['*'],
    dstCluster: data.dstCluster || [],
    renameInfoList: data.renameInfoList || [],
    srcCluster: data.srcCluster || {
      cluster_type: ClusterTypes.SQLSERVER_HA,
      id: 0,
      major_version: '',
      master_domain: '',
    },
  });

  const defaultData = () => ({
    need_auto_rename: false,
    payload: createTickePayload(),
    tableData: [createTableRow()],
    ticketType: TicketTypes.SQLSERVER_INCR_MIGRATE,
  });

  const formData = reactive(defaultData());
  const selected = computed(() =>
    formData.tableData.filter((item) => item.srcCluster.id).map((item) => item.srcCluster),
  );
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.srcCluster.master_domain, true])),
  );

  useTicketDetail<Sqlserver.DataMigrate>(TicketTypes.SQLSERVER_INCR_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        need_auto_rename: details.need_auto_rename,
        ticketType: TicketTypes.SQLSERVER_INCR_MIGRATE,
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const srcCluster = clusters[item.src_cluster];
          return createTableRow({
            dbIgnoreName: item.ignore_db_list,
            dbName: item.db_list,
            dstCluster: item.dst_cluster_list.map((id) => {
              const cluster = clusters[id];
              return {
                cluster_type: cluster.cluster_type as ClusterTypes,
                id: cluster.id,
                major_version: cluster.major_version,
                master_domain: cluster.immute_domain,
              };
            }),
            renameInfoList: item.rename_infos.map((cur) => ({
              db_name: cur.old_db_name,
              rename_cluster_list: [],
              rename_db_name: cur.db_name,
              target_db_name: cur.target_db_name,
            })),
            srcCluster: {
              cluster_type: srcCluster.cluster_type as ClusterTypes,
              id: srcCluster.id,
              major_version: srcCluster.major_version,
              master_domain: srcCluster.immute_domain,
            },
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      db_list: string[];
      dst_cluster_list: number[];
      ignore_db_list: string[];
      rename_infos: {
        db_name: string;
        rename_cluster_list: number[];
        rename_db_name: string;
        target_db_name: string;
      }[];
      src_cluster: number;
    }[];
    need_auto_rename: boolean;
  }>(TicketTypes.SQLSERVER_INCR_MIGRATE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          db_list: item.dbName,
          dst_cluster_list: item.dstCluster.map((cur) => cur.id),
          ignore_db_list: item.dbIgnoreName,
          rename_infos: item.renameInfoList,
          src_cluster: item.srcCluster.id,
        })),
        need_auto_rename: formData.need_auto_rename,
      },
      ...formData.payload,
    });
  };

  const handleMigrateTypeChange = (ticketType: TicketTypes) => {
    router.push({
      name: ticketType,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEditCluster = (list: SqlServerHaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            dbName: ['*'],
            srcCluster: {
              cluster_type: item.cluster_type,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].srcCluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field as keyof RowData]: value,
      });
    });
  };
</script>

<style lang="less" scoped>
  :deep(.bk-form-label) {
    font-size: 12px;
    font-weight: 700;
    color: #313238;
  }
</style>
