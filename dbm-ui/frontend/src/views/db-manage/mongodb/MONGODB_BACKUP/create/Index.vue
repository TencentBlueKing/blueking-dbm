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
    <div class="mongo-db-table-backup-page">
      <BkAlert
        theme="info"
        :title="t('库表备份：指定库表备份，支持模糊匹配')" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <BkFormItem
          :label="t('集群类型')"
          property="cluster_type"
          required>
          <BkRadioGroup
            v-model="formData.cluster_type"
            style="width: 400px"
            type="card">
            <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
              {{ t('副本集集群') }}
            </BkRadioButton>
            <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
              {{ t('分片集群') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          v-if="isShardCluster"
          :label="t('备份位置')"
          property="backup_type"
          required>
          <BkRadioGroup
            v-model="formData.backup_type"
            style="width: 400px"
            type="card">
            <BkRadioButton label="shard"> Shard </BkRadioButton>
            <BkRadioButton label="mongos"> Mongs </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <EditableTable
          :key="renderKey"
          ref="editableTable"
          class="mt16 mb16"
          :model="formData.tableData"
          :rules="rules">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterWithSelectorColumn
              v-if="formData.cluster_type === ClusterTypes.MONGO_REPLICA_SET"
              v-model="item.cluster"
              :cluster-types="[formData.cluster_type]"
              :label="t('副本集')"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <ClusterColumn
              v-if="formData.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER"
              v-model="item.cluster[0]"
              :cluster-types="[formData.cluster_type]"
              field="cluster.0.master_domain"
              :label="t('目标分片集群')"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditTargetHostColumn
              v-if="isShowHostColumn"
              v-model="item.target_host"
              :cluster-id="item.cluster[0].id" />
            <DbNameColumn
              v-model="item.db_patterns"
              field="db_patterns"
              :label="t('备份DB名')"
              @batch-edit="handleDbTableBatchEdit" />
            <DbNameColumn
              v-model="item.ignore_dbs"
              :compare-data="item.ignore_tables"
              field="ignore_dbs"
              :label="t('忽略 DB 名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <TableNameColumn
              v-model="item.table_patterns"
              field="table_patterns"
              :label="t('备份表名')"
              @batch-edit="handleDbTableBatchEdit" />
            <TableNameColumn
              v-model="item.ignore_tables"
              :compare-data="item.ignore_dbs"
              field="ignore_tables"
              :label="t('忽略表名')"
              :required="false"
              @batch-edit="handleDbTableBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <BkFormItem
          :label="t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup
            v-model="formData.file_tag"
            size="small">
            <BkRadio label="normal_backup">
              {{ t('25天') }}
            </BkRadio>
            <BkRadio label="half_year_backup">
              {{ t('6个月') }}
            </BkRadio>
            <BkRadio label="a_year_backup">
              {{ t('1年') }}
            </BkRadio>
            <BkRadio label="forever_backup">
              {{ t('3年') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <TicketPayload v-model="formData" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
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

<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';
  import ClusterWithSelectorColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-with-selector-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mongodb/common/toolbox-field/db-name-column/Index.vue';
  import TableNameColumn from '@views/db-manage/mongodb/common/toolbox-field/table-name-column/Index.vue';

  import EditTargetHostColumn from './components/TargetHostColumn.vue';

  interface IDataRow {
    cluster: {
      id: number;
      master_domain: string;
      cluster_type: string;
      cluster_type_name: string;
    }[];
    target_host: string;
    db_patterns: string[];
    ignore_dbs: string[];
    table_patterns: string[];
    ignore_tables: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: values.cluster
      ? values.cluster
      : [
          {
            id: 0,
            master_domain: '',
            cluster_type: '',
            cluster_type_name: '',
          },
        ],
    target_host: values.target_host || '',
    db_patterns: values.db_patterns || [],
    ignore_dbs: values.ignore_dbs || [],
    table_patterns: values.table_patterns || [],
    ignore_tables: values.ignore_tables || [],
  });

  const createDefaultFormData = () => ({
    tableData: [createRowData()],
    cluster_type: ClusterTypes.MONGO_REPLICA_SET,
    backup_type: 'shard',
    file_tag: 'normal_backup',
    ...createTickePayload(),
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.Backup>(TicketTypes.MONGODB_BACKUP, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters, backup_type: backupType, file_tag } = details;
      Object.assign(formData, {
        cluster_type: clusters[infos[0].cluster_ids[0]].cluster_type,
        backup_type: backupType || 'shard',
        file_tag,
        remark,
      });

      nextTick(() => {
        formData.tableData = infos.map((item) =>
          createRowData({
            cluster: item.cluster_ids.map((clusterId) => ({
              master_domain: clusters[clusterId].immute_domain,
            })) as IDataRow['cluster'],
            target_host: item.backup_host,
            db_patterns: item.ns_filter.db_patterns,
            ignore_dbs: item.ns_filter.ignore_dbs,
            table_patterns: item.ns_filter.table_patterns,
            ignore_tables: item.ns_filter.ignore_tables,
          }),
        );
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    file_tag: string;
    backup_type?: string;
    infos: {
      cluster_ids: number[];
      cluster_type: string;
      ns_filter: {
        db_patterns: string[];
        ignore_dbs: string[];
        table_patterns: string[];
        ignore_tables: string[];
      };
      backup_host?: string;
    }[];
  }>(TicketTypes.MONGODB_BACKUP);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    cluster: [
      {
        validator: (value: IDataRow['cluster']) => {
          const currentRowDomainMap = value.reduce<Record<string, number>>((prevMap, item) => {
            if (item.master_domain) {
              return Object.assign({}, prevMap, { [item.master_domain]: 0 });
            }
            return prevMap;
          }, {});
          formData.tableData.forEach((rowItem) => {
            rowItem.cluster.forEach((clusterItem) => {
              if (clusterItem.master_domain && currentRowDomainMap[clusterItem.master_domain] !== undefined) {
                currentRowDomainMap[clusterItem.master_domain] = currentRowDomainMap[clusterItem.master_domain] + 1;
              }
            });
          });
          const unValidRowDomainMapList = Object.entries(currentRowDomainMap).filter((mapItem) => mapItem[1] > 1);
          const unValidRowDomainList = unValidRowDomainMapList.map((item) => item[0]);
          if (unValidRowDomainList.length > 0) {
            return t('目标集群n重复', { n: unValidRowDomainList.join('，') });
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
  };

  const formData = reactive(createDefaultFormData());

  const renderKey = computed(() => `${formData.cluster_type}-${formData.backup_type}`);
  const isShardCluster = computed(() => formData.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER);
  const isShowHostColumn = computed(() => isShardCluster.value && formData.backup_type === 'mongos');

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterWithSelectorColumn>['selected'] = {
      [formData.cluster_type]: [],
    };
    formData.tableData.forEach((tableRow) => {
      tableRow.cluster.forEach((clusterItem) => {
        const { id, cluster_type: clusterType, master_domain: masterDomain } = clusterItem;
        if (id) {
          selectedClusters[clusterType as keyof typeof selectedClusters].push({
            id,
            master_domain: masterDomain,
          });
        }
      });
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  watch(
    () => formData.cluster_type,
    () => {
      formData.tableData = [createRowData()];
    },
  );

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      const details = {
        file_tag: formData.file_tag,
        infos: formData.tableData.map((tableRow) => {
          const result = {
            cluster_ids: tableRow.cluster.map((item) => item.id),
            cluster_type: formData.cluster_type,
            ns_filter: {
              db_patterns: tableRow.db_patterns,
              ignore_dbs: tableRow.ignore_dbs,
              table_patterns: tableRow.table_patterns,
              ignore_tables: tableRow.ignore_tables,
            },
          };
          if (isShowHostColumn.value) {
            Object.assign(result, {
              backup_host: tableRow.target_host,
            });
          }
          return result;
        }),
      };
      if (isShardCluster.value) {
        Object.assign(details, {
          backup_type: formData.backup_type,
        });
      }

      createTicketRun({
        details,
        remark: formData.remark,
      });
    }
  };

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: [
              {
                id: item.id,
                master_domain: item.master_domain,
                cluster_type: item.cluster_type,
                cluster_type_name: item.cluster_type_name,
              },
            ],
          }),
        );
      }
    });

    formData.tableData = [...(_.isEmpty(formData.tableData[0].cluster) ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleDbTableBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .mongo-db-table-backup-page {
    padding-bottom: 20px;
  }
</style>
