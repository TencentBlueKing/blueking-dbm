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
    <div class="proxy-scale-down-page">
      <BkAlert
        closable
        theme="info"
        :title="t('缩容接入层：减加集群的Proxy数量，但集群Proxy数量不能少于2')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="tableData"
          :rules="rules">
          <EditableTableRow
            v-for="(item, index) in tableData"
            :key="index">
            <EditClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
              field="cluster.master_domain"
              :label="t('目标分片集群')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableTableColumn
              field="cluster.id"
              :label="t('缩容节点类型')"
              :width="200">
              <span class="ml-8">mongos</span>
            </EditableTableColumn>
            <SpecBlockColumn
              :data="item.cluster?.mongos?.[0].spec_config"
              :label="t('当前规格')"
              :placeholder="t('输入集群后自动生成')" />
            <IpSelectColumn
              v-model="item.reduce_nodes"
              :affinity="item.cluster.affinity"
              :data-list="item.cluster.mongos"
              :disabled="!item.cluster.id" />
            <EditableTableColumn
              :label="t('缩容数量（台）')"
              required
              :width="200">
              <EditInput
                v-model="item.reduce_nodes.length"
                disabled
                :max="(item.cluster.mongos?.length || 0) - 2"
                :min="1"
                :placeholder="t('请输入缩容数量')"
                :rules="rules"
                type="number" />
            </EditableTableColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="tableData" />
          </EditableTableRow>
        </EditableTable>
        <IgnoreBiz
          v-model="formData.ignore_business_access"
          v-bk-tooltips="t('如忽略_有连接的情况下也会执行')" />
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
          class="ml-8 w-88"
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

  import { type TabItem } from '@components/cluster-selector/Index.vue';
  import EditableTable, {
    Column as EditableTableColumn,
    Input as EditInput,
    Row as EditableTableRow,
  } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import SpecBlockColumn from '@views/db-manage/common/toolbox-field/column/spec-block-column/Index.vue';
  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/form-item/ticket-remark/Index.vue';
  import EditClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-column/Index.vue';

  import IpSelectColumn from './components/IpSelectColumn.vue';

  export interface IDataRow {
    cluster: {
      id?: number;
      master_domain?: string;
      mongos?: MongodbModel['mongos'];
      affinity?: string;
    };
    reduce_nodes: string[];
  }

  const createRowData = (values?: Partial<IDataRow>) => ({
    cluster: values?.cluster ? values.cluster : ({} as IDataRow['cluster']),
    reduce_nodes: values?.reduce_nodes || [],
  });

  const createDefaultFormData = () => ({
    ignore_business_access: false,
    remark: '',
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.ReduceMongos>(TicketTypes.MONGODB_REDUCE_MONGOS, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters, is_safe: isSafe } = details;

      tableData.value = infos.map((infoItem) =>
        createRowData({
          cluster: {
            master_domain: clusters[infoItem.cluster_id].immute_domain,
          },
          reduce_nodes: infoItem.reduce_nodes.map((item) => item.ip),
        }),
      );
      Object.assign(formData, {
        ignore_business_access: !isSafe,
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      cluster_id: number;
      reduce_nodes: {
        ip: string;
        bk_host_id: number;
        bk_cloud_id: number;
      }[];
      role: string;
    }[];
    is_safe: boolean;
  }>(TicketTypes.MONGODB_REDUCE_MONGOS);

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = tableData.value.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
  };

  const tabListConfig = {
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: MongodbModel) => data.mongos.length < 2,
          tip: t('Proxy数量不足，至少 2 台'),
        },
      ],
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const tableData = ref([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof EditClusterColumn>['selected'] = {
      [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    };
    tableData.value.forEach((tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id && masterDomain) {
        selectedClusters[ClusterTypes.MONGO_SHARED_CLUSTER].push({
          id,
          master_domain: masterDomain,
        });
      }
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

  // 批量选择
  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              id: item.id,
              master_domain: item.master_domain,
              mongos: item.mongos,
            },
          }),
        );
      }
    });

    tableData.value = [...(_.isEmpty(tableData.value[0].cluster) ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      const details = {
        is_safe: !formData.ignore_business_access,
        infos: tableData.value.map((tableItem) => {
          const selectMap = tableItem.cluster.mongos!.reduce<Record<string, MongodbModel['mongos'][number]>>(
            (results, item) => {
              Object.assign(results, {
                [item.ip]: item,
              });
              return results;
            },
            {},
          );
          return {
            cluster_id: tableItem.cluster.id!,
            role: 'mongos',
            reduce_nodes: tableItem.reduce_nodes.map((item) => {
              const selectItem = selectMap[item];
              return {
                ip: item,
                bk_cloud_id: selectItem.bk_cloud_id,
                bk_host_id: selectItem.bk_host_id,
              };
            }),
          };
        }),
      };
      createTicketRun({
        details,
        remark: formData.remark,
      });
    }
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    tableData.value = [createRowData()];
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-down-page {
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
