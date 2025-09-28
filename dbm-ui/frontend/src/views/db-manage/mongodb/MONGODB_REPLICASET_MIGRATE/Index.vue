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
    <div class="mongodb-replicaset-migrate-page db-toolbox">
      <BkAlert
        closable
        theme="info"
        :title="t('迁移：将指定副本集、分片迁移至新机器')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <MigrateFormItem v-model="formData.architectureType" />
        <BatchInput
          :config="batchInputConfig"
          @change="handleBatchInput" />
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterBatchColumn
              v-model="item.batchCluster"
              :selected="selected"
              :selected-map="selectedMap"
              @batch-edit="handleClusterBatchEdit" />
            <RelatedInstanceColumn
              v-model="item.batchCluster.related_instances"
              :clusters="item.batchCluster.clusters" />
            <SpecColumn
              v-model="item.target_spec_id"
              :cluster-type="DBTypes.MONGODB"
              :current-spec-id-list="
                Object.values(item.batchCluster.clusters).flatMap((item) =>
                  item.mongodb.map((mongodbItem) => mongodbItem.spec_config.id),
                )
              "
              field="target_spec_id"
              label="目标规格"
              :machine-type="MachineTypes.MONGODB"
              required
              selectable
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
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
          class="ml-8 w-88"
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

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import MigrateFormItem from '@views/db-manage/mongodb/common/migrate-form-item/Index.vue';

  import { random } from '@utils';

  import ClusterBatchColumn from './components/ClusterBatchColumn.vue';
  import RelatedInstanceColumn from './components/RelatedInstanceColumn.vue';

  interface IDataRow {
    batchCluster: ComponentProps<typeof ClusterBatchColumn>['modelValue'];
    target_spec_id: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    batchCluster: Object.assign(
      {
        clusters: {} as IDataRow['batchCluster']['clusters'],
        related_instances: [] as IDataRow['batchCluster']['related_instances'],
        renderText: '',
      },
      values.batchCluster,
    ),
    target_spec_id: values.target_spec_id || 0,
  });

  const createDefaultFormData = () => ({
    architectureType: TicketTypes.MONGODB_REPLICASET_MIGRATE,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.ReplicasetMigrate>(TicketTypes.MONGODB_REPLICASET_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;

      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          const domainList = item.cluster_ids.map((clusterId) => clusters[clusterId].immute_domain);
          return createRowData({
            batchCluster: {
              renderText: domainList.join('\n'),
            } as IDataRow['batchCluster'],
            target_spec_id: item.resource_spec.mongodb.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      current_replicaset_nodes_num: number; // 当前一个副本集的节点数量
      db_version: string;
      disaster_tolerance_level: string;
      old_nodes: {
        replicaset: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      related_instances: {
        domain: string;
        instances: string[];
      }[]; // 展示用
      resource_spec: {
        mongodb: {
          count: number;
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MONGODB_REPLICASET_MIGRATE);

  const batchInputConfig = [
    {
      case: 'mongodb.test.1.db\\nmongodb.test.2.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: t('无限制'),
      key: 'spec_name',
      label: t('目标规格'),
    },
  ];

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() =>
    formData.tableData
      .filter((item) => item.batchCluster.renderText)
      .flatMap((item) => Object.values(item.batchCluster.clusters)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            batchCluster: {
              renderText: item.master_domain,
            } as IDataRow['batchCluster'],
          }),
        );
      }
    });

    formData.tableData = [...formData.tableData.filter((item) => item.batchCluster.renderText), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          batchCluster: {
            renderText: item.master_domain?.replaceAll('\\n', '\n') || '',
          } as IDataRow['batchCluster'],
          target_spec_id: item.spec_name,
        }),
      );
      return acc;
    }, []);

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...newList];
    } else {
      formData.tableData = [...formData.tableData.filter((item) => item.batchCluster.renderText), ...newList];
    }

    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => {
            // 取首个集群信息，给定校验基准
            const clusterInfo = Object.values(tableItem.batchCluster.clusters)[0];
            const oldNodes = _.uniqBy(
              Object.values(tableItem.batchCluster.clusters).flatMap((clusterItem) =>
                clusterItem.mongodb.map((mongodbItem) => ({
                  bk_biz_id: mongodbItem.bk_biz_id,
                  bk_cloud_id: mongodbItem.bk_cloud_id,
                  bk_host_id: mongodbItem.bk_host_id,
                  ip: mongodbItem.ip,
                })),
              ),
              'bk_host_id',
            );
            return {
              cluster_ids: Object.values(tableItem.batchCluster.clusters).map((clusterItem) => clusterItem.id),
              current_replicaset_nodes_num: clusterInfo.mongodb.length,
              db_version: clusterInfo.major_version,
              disaster_tolerance_level: clusterInfo.disaster_tolerance_level,
              old_nodes: {
                replicaset: oldNodes,
              },
              related_instances: tableItem.batchCluster.related_instances,
              resource_spec: {
                mongodb: {
                  count: 1 * clusterInfo.shard_node_count, // 迁移到同一组
                  spec_id: tableItem.target_spec_id,
                },
              },
            };
          }),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .mongodb-replicaset-migrate-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
