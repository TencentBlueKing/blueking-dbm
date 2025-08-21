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
      :title="t('添加从库_同机的所有集群会统一新增从库_但新机器不添加到域名解析中去')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <WithRelatedClustersColumn
            v-model="item.cluster"
            allow-repeat
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SingleResourceHostColumn
            v-model="item.newSlave"
            field="newSlave.ip"
            :label="t('新从库主机')"
            :min-width="150"
            :params="{
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.MYSQL, 'PUBLIC'],
            }" />
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
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: ComponentProps<typeof WithRelatedClustersColumn>['modelValue'];
    newSlave: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '192.168.10.2',
      key: 'new_slave_ip',
      label: t('新从库主机'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        cluster_type: ClusterTypes.TENDBHA,
        id: 0,
        master_domain: '',
        region: '',
        related_clusters: [] as RowData['cluster']['related_clusters'],
        spec_id_list: [] as RowData['cluster']['spec_id_list'],
      },
      data.cluster,
    ),
    newSlave: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.newSlave,
    ),
  });

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const clusterMap = computed(() => {
    return formData.tableData.reduce<Record<string, string>>((acc, cur) => {
      Object.assign(acc, {
        [cur.cluster.master_domain]: cur.cluster.master_domain,
      });
      cur.cluster.related_clusters.forEach((item) => {
        Object.assign(acc, {
          [item.master_domain]: cur.cluster.master_domain, // 关联集群映射到所属集群
        });
      });
      return acc;
    }, {});
  });
  const newSlaveCounter = computed(() => {
    return formData.tableData.reduce<Record<string, number>>((result, item) => {
      Object.assign(result, {
        [item.newSlave.ip]: (result[item.newSlave.ip] || 0) + 1,
      });
      return result;
    }, {});
  });

  const rules = {
    'cluster.master_domain': [
      {
        message: '',
        trigger: 'blur',
        validator: (value: string) => {
          const target = clusterMap.value[value];
          if (target && target !== value) {
            return t('目标集群是集群target的关联集群_请勿重复添加', { target });
          }
          return true;
        },
      },
    ],
    'newSlave.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newSlaveCounter.value[row.newSlave.ip] <= 1;
        },
      },
      {
        message: t('IP 重复'),
        trigger: 'change',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newSlaveCounter.value[row.newSlave.ip] <= 1;
        },
      },
    ],
  };

  useTicketDetail<Mysql.ResourcePool.AddSlave>(TicketTypes.MYSQL_ADD_SLAVE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { backup_source: backupSource, clusters, infos } = details;
      Object.assign(formData, {
        backupSource,
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          return createTableRow({
            cluster: {
              master_domain: clusters[item.cluster_ids[0]]?.immute_domain || '',
            },
            newSlave: {
              ip: item.resource_spec.new_slave.hosts?.[0]?.ip || '',
            },
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_ids: number[];
      resource_spec: {
        new_slave: {
          hosts: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_ADD_SLAVE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        backup_source: formData.backupSource,
        infos: formData.tableData.map((item) => ({
          cluster_ids: [item.cluster.id, ...item.cluster.related_clusters.map((item) => item.id)],
          resource_spec: {
            new_slave: {
              hosts: [item.newSlave],
              spec_id: item.cluster.spec_id_list[0],
            },
          },
        })),
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!clusterMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          cluster: {
            master_domain: item.master_domain,
          },
          newSlave: {
            ip: item.new_slave_ip,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };
</script>
<style lang="less" scoped>
  :deep(.is-error .related-clusters) {
    background: initial;
  }
</style>
