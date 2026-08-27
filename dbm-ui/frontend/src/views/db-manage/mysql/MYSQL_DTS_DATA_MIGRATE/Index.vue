<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
-->

<template>
  <DtsMigrateWrapper>
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="tableRef"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.source_cluster"
            allow-repeat
            field="source_cluster.master_domain"
            :label="t('源集群')"
            :selected="selectedSourceClusters"
            @batch-edit="handleBatchEditSourceCluster" />
          <DbNameColumn
            v-model="item.source_db_list"
            check-not-exist
            :cluster-id="item.source_cluster?.id"
            field="source_db_list"
            :label="t('源 DB')"
            required
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_db_list"
            :cluster-id="item.source_cluster?.id"
            field="ignore_db_list"
            :label="t('忽略 DB')"
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.source_table_list"
            check-not-exist
            :cluster-id="item.source_cluster?.id"
            field="source_table_list"
            :label="t('源表')"
            required
            @batch-edit="handleBatchEdit" />
          <TableNameColumn
            v-model="item.ignore_table_list"
            :cluster-id="item.source_cluster?.id"
            field="ignore_table_list"
            :label="t('忽略表')"
            @batch-edit="handleBatchEdit" />
          <TargetClusterColumn
            v-model="item.target_cluster"
            :cluster="item.source_cluster"
            :selected="selectedTargetClusters"
            source-field="source_cluster" />
          <SpecColumn
            v-model="item.spec_id"
            :cluster-type="DBTypes.MYSQL"
            :current-spec-id-list="getSpecIdList(item.source_cluster)"
            field="spec_id"
            :machine-type="MachineTypes.MYSQL_BACKEND"
            required
            selectable
            @batch-edit="handleBatchEdit" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEdit" />
          <AvailableResourceColumn
            :params="{
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.MYSQL, 'PUBLIC'],
              spec_id: item.spec_id,
              labels: item.labels.map((label) => label.id).join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem
        :label="t('数据冲突处理')"
        required>
        <BkRadioGroup v-model="formData.conflictHandle">
          <BkRadio label="replace">
            {{ t('覆盖旧数据') }}
          </BkRadio>
          <BkRadio label="ignore">
            {{ t('保留旧数据') }}
          </BkRadio>
          <BkRadio label="error">
            {{ t('报错并停止') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
      <template #action>
        <BkButton
          class="mr-8 w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbResetButton
          class="ml-8"
          :confirm-handler="handleReset"
          :disabled="isSubmitting" />
      </template>
    </SmartAction>
  </DtsMigrateWrapper>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mysql/common/toolbox-field/table-name-column/Index.vue';
  import TargetClusterColumn from '@views/db-manage/mysql/common/toolbox-field/target-cluster-column/Index.vue';

  import { random } from '@utils';

  import DtsMigrateWrapper from './components/DtsMigrateWrapper.vue';

  interface RowData {
    ignore_db_list: string[];
    ignore_table_list: string[];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    source_cluster: TendbhaModel;
    source_db_list: string[];
    source_table_list: string[];
    spec_id: number;
    target_cluster: {
      cluster_type: string;
      id: number;
      master_domain: string;
    };
  }

  defineOptions({
    name: TicketTypes.MYSQL_DTS_DATA_MIGRATE,
  });

  const { t } = useI18n();
  const router = useRouter();

  const tableRef = useTemplateRef('tableRef');
  const tableKey = ref(random());
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'source_master_domain',
      label: t('源集群'),
    },
    {
      case: '*',
      key: 'source_db_list',
      label: t('源 DB'),
    },
    {
      case: 'NULL',
      key: 'ignore_db_list',
      label: t('忽略 DB'),
    },
    {
      case: '*',
      key: 'source_table_list',
      label: t('源表'),
    },
    {
      case: 'NULL',
      key: 'ignore_table_list',
      label: t('忽略表'),
    },
    {
      case: 'tendbha2.test.dba.db',
      key: 'target_master_domain',
      label: t('目标集群'),
    },
    {
      case: '2核_4G_50G',
      key: 'spec_name',
      label: t('DTS 规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    ignore_db_list: data.ignore_db_list || [],
    ignore_table_list: data.ignore_table_list || [],
    labels: data.labels || [],
    source_cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.source_cluster,
    ),
    source_db_list: data.source_db_list || [],
    source_table_list: data.source_table_list || [],
    spec_id: data.spec_id || 0,
    target_cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      },
      data.target_cluster,
    ),
  });

  const defaultData = () => ({
    conflictHandle: 'error' as 'error' | 'replace' | 'ignore',
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selectedSourceClusters = computed(() =>
    formData.tableData.filter((item) => item.source_cluster.id).map((item) => item.source_cluster),
  );

  const selectedTargetClusters = computed(() =>
    formData.tableData
      .filter((item) => item.target_cluster.id)
      .map((item) => ({ id: item.target_cluster.id, master_domain: item.target_cluster.master_domain })),
  );

  const getSpecIdList = (cluster: TendbhaModel) => {
    if (!cluster || !cluster.id) {
      return [];
    }
    const instances = [...(cluster.masters || []), ...(cluster.slaves || [])];
    return instances.map((item) => item.spec_config.id);
  };

  useTicketDetail<Mysql.DtsDataMigrate>(TicketTypes.MYSQL_DTS_DATA_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters } = details;
      const tableData = details.infos.map((item) =>
        createTableRow({
          ignore_db_list: item.migrate.one_to_one.source.sync_scope.ignore_dbs || [],
          ignore_table_list: (item.migrate.one_to_one.source.sync_scope.ignore_tables || []).map(
            (tableItem) => tableItem.table,
          ),
          labels: (item.resource_spec?.master?.labels || []).map((labelId, index) => ({
            id: Number(labelId),
            value: item.resource_spec?.master?.label_names?.[index] || '',
          })) as RowData['labels'],
          source_cluster: {
            master_domain: clusters?.[item.migrate.one_to_one.source.cluster_id]?.immute_domain || '',
          } as TendbhaModel,
          source_db_list: item.migrate.one_to_one.source.sync_scope.do_dbs || [],
          source_table_list: (item.migrate.one_to_one.source.sync_scope.do_tables || []).map(
            (tableItem) => tableItem.table,
          ),
          spec_id: item.resource_spec?.master?.spec_id || 0,
          target_cluster: {
            master_domain: clusters?.[item.migrate.one_to_one.target.cluster_id]?.immute_domain || '',
          } as RowData['target_cluster'],
        }),
      );
      Object.assign(formData, {
        conflictHandle: details.task?.on_duplicate || 'error',
        payload: createTicketPayload(ticketDetail),
        tableData: tableData.length ? tableData : [createTableRow()],
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      dts_resource: {
        deploy: Record<string, never>;
      };
      migrate: {
        one_to_one: {
          source: {
            cluster_id: number;
            sync_scope: {
              do_dbs: string[];
              do_tables: { db: string; table: string }[];
              ignore_dbs: string[];
              ignore_tables: { db: string; table: string }[];
            };
          };
          target: {
            cluster_id: number;
          };
        };
        topology: 'one_to_one';
      };
      resource_spec: {
        master: {
          count: number;
          label_names: string[];
          labels: string[];
          spec_id: number;
        };
        worker: {
          count: number;
          label_names: string[];
          labels: string[];
          spec_id: number;
        };
      };
    }[];
    task: {
      on_duplicate: 'error' | 'replace' | 'ignore';
    };
  }>(TicketTypes.MYSQL_DTS_DATA_MIGRATE);

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          dts_resource: {
            deploy: {},
          },
          migrate: {
            one_to_one: {
              source: {
                cluster_id: item.source_cluster.id,
                sync_scope: {
                  do_dbs: item.source_db_list,
                  do_tables: item.source_db_list.flatMap((db) =>
                    item.source_table_list.map((table) => ({ db, table })),
                  ),
                  ignore_dbs: item.ignore_db_list,
                  ignore_tables: item.ignore_table_list.flatMap((table) =>
                    item.ignore_db_list.length > 0
                      ? item.ignore_db_list.map((db) => ({ db, table }))
                      : item.source_db_list.map((db) => ({ db, table })),
                  ),
                },
              },
              target: {
                cluster_id: item.target_cluster.id,
              },
            },
            topology: 'one_to_one' as const,
          },
          resource_spec: {
            master: {
              count: 1,
              label_names: item.labels.map((label) => label.value),
              labels: item.labels.map((item) => String(item.id)),
              spec_id: item.spec_id,
            },
            worker: {
              count: 1,
              label_names: item.labels.map((label) => label.value),
              labels: item.labels.map((item) => String(item.id)),
              spec_id: item.spec_id,
            },
          },
        })),
        task: {
          on_duplicate: formData.conflictHandle,
        },
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
  };

  const handleBatchEditSourceCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      acc.push(
        createTableRow({
          source_cluster: {
            master_domain: cluster.master_domain,
          } as TendbhaModel,
        }),
      );
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        ignore_db_list: item.ignore_db_list ? item.ignore_db_list.split('\n') : [],
        ignore_table_list: item.ignore_table_list ? item.ignore_table_list.split('\n') : [],
        labels: ((item.labels as string)?.split(',').map((label) => ({ value: label })) || []) as RowData['labels'],
        source_cluster: {
          master_domain: item.source_master_domain,
        } as TendbhaModel,
        source_db_list: item.source_db_list ? item.source_db_list.split('\n') : [],
        source_table_list: item.source_table_list ? item.source_table_list.split('\n') : [],
        spec_id: item.spec_name,
        target_cluster: {
          master_domain: item.target_master_domain,
        } as RowData['target_cluster'],
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
