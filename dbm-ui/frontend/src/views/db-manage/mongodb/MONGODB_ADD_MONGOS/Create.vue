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
    <div class="proxy-scale-up-page">
      <BkAlert
        closable
        theme="info"
        :title="t('扩容接入层：增加集群的Proxy数量，新Proxy可以指定规格')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="formData.tableData"
          :rules="rules">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
              field="cluster.master_domain"
              :label="t('目标分片集群')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              field="cluster.id"
              :label="t('扩容节点类型')"
              :width="200">
              <EditableBlock>mongos</EditableBlock>
            </EditableColumn>
            <EditSpecColumn
              v-model="item.spec_id"
              :current-spec-ids="item.cluster.mongos.length ? [item.cluster.mongos[0].spec_config.id] : []"
              field="spec_id"
              :label="t('扩容规格')"
              :params="{
                clusterType: ClusterTypes.MONGODB,
                machineType: MachineTypes.MONGOS,
                bkCloudId: item.cluster.bk_cloud_id,
              }" />
            <EditableColumn
              field="target_num"
              :label="t('扩容数量（台）')"
              required
              :width="300">
              <EditableInput
                v-model="item.target_num"
                :min="1"
                :placeholder="t('不能少于n台', { n: 1 })"
                :rules="rules"
                type="number" />
            </EditableColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, MachineTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import EditSpecColumn from '@views/db-manage/common/toolbox-field/column/spec-select-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  export interface IDataRow {
    cluster: {
      id: number;
      master_domain: string;
      mongos: MongodbModel['mongos'];
      bk_cloud_id: number;
    };
    spec_id: number;
    target_num: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
        mongos: [] as MongodbModel['mongos'],
        bk_cloud_id: 0,
      },
      values.cluster,
    ),
    spec_id: values.spec_id || 0,
    target_num: values.target_num || 0,
  });

  const createDefaultFormData = () => ({
    tableData: [createRowData()],
    ...createTickePayload(),
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.AddMongos>(TicketTypes.MONGODB_ADD_MONGOS, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;

      Object.assign(formData, {
        tableData: infos.map((infoItem) =>
          createRowData({
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            spec_id: infoItem.resource_spec.mongos.spec_id,
            target_num: infoItem.resource_spec.mongos.count,
          }),
        ),
        remark,
      });
    },
  });

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<{
    infos: {
      cluster_id: number;
      role: string;
      resource_spec: {
        mongos: {
          spec_id: number;
          count: number;
        };
      };
    }[];
  }>(TicketTypes.MONGODB_ADD_MONGOS);

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = formData.tableData.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
    target_num: [
      {
        validator: (value: string) => Number(value) >= 1,
        trigger: 'change',
        message: t('不能少于n台', { n: 1 }),
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

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => {
    const selectedClusterList = formData.tableData.reduce<
      {
        id: number;
        master_domain: string;
      }[]
    >((prevList, tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id) {
        return prevList.concat({
          id,
          master_domain: masterDomain,
        });
      }
      return prevList;
    }, []);
    return {
      [ClusterTypes.MONGO_SHARED_CLUSTER]: selectedClusterList,
    };
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            cluster_id: tableItem.cluster.id,
            role: 'mongos',
            resource_spec: {
              mongos: {
                spec_id: tableItem.spec_id,
                count: tableItem.target_num,
              },
            },
          })),
        },
        remark: formData.remark,
      });
    }
  };

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
              bk_cloud_id: item.bk_cloud_id,
            },
          }),
        );
      }
    });

    formData.tableData = [...(formData.tableData[0].cluster.master_domain ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-up-page {
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

  .bottom-btn {
    width: 88px;
  }
</style>
