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
    <div class="mongo-db-clear-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')
        " />
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
        <EditableTable
          :key="formData.cluster_type"
          ref="editableTable"
          class="mt16 mb16"
          :model="tableData"
          :rules="rules">
          <EditableTableRow
            v-for="(item, index) in tableData"
            :key="index">
            <EditClusterColumn
              v-if="isShardCluster"
              v-model="item.cluster[0]"
              :cluster-types="[formData.cluster_type]"
              field="cluster.0.master_domain"
              :label="t('目标分片集群')"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditClusterWithSelectorColumn
              v-else
              v-model="item.cluster"
              :cluster-types="[formData.cluster_type]"
              :label="t('副本集')"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <DropTypeColumn v-model="item.drop_type" />
            <DropIndexColumn v-model="item.drop_index" />
            <EditDbNameColumn
              v-model="item.db_patterns"
              field="db_patterns"
              :label="t('备份DB名')"
              @batch-edit="(value: string[]) => handleDbTableBatchEdit(value, 'db_patterns')" />
            <EditDbNameColumn
              v-model="item.ignore_dbs"
              :compare-data="item.ignore_tables"
              field="ignore_dbs"
              :label="t('忽略 DB 名')"
              :required="false"
              @batch-edit="(value: string[]) => handleDbTableBatchEdit(value, 'ignore_dbs')" />
            <EditTableNameColumn
              v-model="item.table_patterns"
              field="table_patterns"
              :label="t('备份表名')"
              @batch-edit="(value: string[]) => handleDbTableBatchEdit(value, 'table_patterns')" />
            <EditTableNameColumn
              v-model="item.ignore_tables"
              :compare-data="item.ignore_dbs"
              field="ignore_tables"
              :label="t('忽略表名')"
              :required="false"
              @batch-edit="(value: string[]) => handleDbTableBatchEdit(value, 'ignore_tables')" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="tableData" />
          </EditableTableRow>
        </EditableTable>
        <div class="bottom-opeartion">
          <BkCheckbox
            v-model="formData.ignore_business_access"
            style="padding-top: 6px" />
          <span
            v-bk-tooltips="{
              content: t('如忽略_有连接的情况下也会执行'),
              theme: 'dark',
            }"
            class="ml-6 force-switch">
            {{ t('忽略业务连接') }}
          </span>
        </div>
        <TicketRemark v-model="formData.remark" />
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
<script setup lang="tsx">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';
  import { createTicket } from '@services/source/ticket';

  import { useTicketDetail } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import EditableTable, { Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import TicketRemark from '@views/db-manage/common/TicketRemark.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import EditClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-column/Index.vue';
  import EditClusterWithSelectorColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-with-selector-column/Index.vue';
  import EditDbNameColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-db-name-column/Index.vue';
  import EditTableNameColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-table-name-column/Index.vue';

  import DropTypeColumn from './components/DropTypeColumn.vue';
  import DropIndexColumn from './components/DropTypeIndex.vue';

  export interface IDataRow {
    cluster: {
      id?: number;
      master_domain?: string;
      cluster_type?: string;
    }[];
    drop_type: string;
    drop_index: string;
    db_patterns: string[];
    ignore_dbs: string[];
    table_patterns: string[];
    ignore_tables: string[];
  }

  const createRowData = (values?: Partial<IDataRow>) => ({
    cluster: values?.cluster ? values.cluster : [{}],
    drop_type: values?.drop_type || '',
    drop_index: values?.drop_index || '',
    db_patterns: values?.db_patterns || [],
    ignore_dbs: values?.ignore_dbs || [],
    table_patterns: values?.table_patterns || [],
    ignore_tables: values?.ignore_tables || [],
  });

  const createDefaultFormData = () => ({
    cluster_type: ClusterTypes.MONGO_REPLICA_SET,
    ignore_business_access: false,
    remark: '',
  });

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  useTicketDetail<Mongodb.RemoveNs>(TicketTypes.MONGODB_REMOVE_NS, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters, is_safe: isSafe } = details;
      Object.assign(formData, {
        cluster_type: clusters[infos[0].cluster_ids[0]].cluster_type,
        ignore_business_access: !isSafe,
        remark,
      });

      nextTick(() => {
        tableData.value = infos.map((item) =>
          createRowData({
            cluster: item.cluster_ids.map((clusterId) => ({
              master_domain: clusters[clusterId].immute_domain,
            })),
            drop_type: item.drop_type,
            drop_index: item.drop_index ? 'delete' : 'keep',
            db_patterns: item.ns_filter.db_patterns,
            ignore_dbs: item.ns_filter.ignore_dbs,
            table_patterns: item.ns_filter.table_patterns,
            ignore_tables: item.ns_filter.ignore_tables,
          }),
        );
      });
    },
  });

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
          tableData.value.forEach((rowItem) => {
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

  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const selectedClusters = shallowRef<{ [key: string]: Array<MongodbModel> }>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const formData = reactive(createDefaultFormData());

  const isShardCluster = computed(() => formData.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER);

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof EditClusterWithSelectorColumn>['selected'] = {
      [formData.cluster_type]: [],
    };
    tableData.value.forEach((tableRow) => {
      tableRow.cluster.forEach((clusterItem) => {
        const { id, cluster_type: clusterType, master_domain: masterDomain } = clusterItem;
        if (id && clusterType && masterDomain) {
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
      tableData.value = [createRowData()];
    },
  );

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
              },
            ],
          }),
        );
      }
    });

    tableData.value = [...(_.isEmpty(tableData.value[0].cluster) ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const handleDbTableBatchEdit = (value: string[], field: keyof Omit<IDataRow, 'cluster' | 'target_host'>) => {
    tableData.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      await formRef.value!.validate();
      const validateResult = await editableTableRef.value!.validate();
      if (validateResult) {
        const params = {
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.MONGODB_REMOVE_NS,
          remark: formData.remark,
          details: {
            is_safe: !formData.ignore_business_access,
            infos: tableData.value.map((tableRow) => ({
              cluster_ids: tableRow.cluster.map((item) => item.id),
              cluster_type: formData.cluster_type,
              drop_type: tableRow.drop_type,
              drop_index: tableRow.drop_index !== 'keep',
              ns_filter: {
                db_patterns: tableRow.db_patterns,
                ignore_dbs: tableRow.ignore_dbs,
                table_patterns: tableRow.table_patterns,
                ignore_tables: tableRow.ignore_tables,
              },
            })),
          },
        };
        await createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: TicketTypes.MONGODB_REMOVE_NS,
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        });
      }
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[formData.cluster_type] = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mongo-db-clear-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 20px;

      .safe-action-text {
        padding-bottom: 2px;
        border-bottom: 1px dashed #979ba5;
      }
    }

    .bottom-opeartion {
      display: flex;
      width: 100%;
      height: 30px;
      align-items: flex-end;
      margin-bottom: 24px;

      .force-switch {
        font-size: 12px;
        border-bottom: 1px dashed #63656e;
      }
    }
  }
</style>
