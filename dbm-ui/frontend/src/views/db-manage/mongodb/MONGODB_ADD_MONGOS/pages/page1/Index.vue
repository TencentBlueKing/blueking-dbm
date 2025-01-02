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
          :model="tableData"
          :rules="rules">
          <EditableTableRow
            v-for="(item, index) in tableData"
            :key="index">
            <EditClusterColumn
              v-model="item.cluster"
              :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
              field="cluster.master_domain"
              label="目标分片集群"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableTableColumn
              field="cluster.id"
              :label="t('扩容节点类型')"
              :width="200">
              <span class="ml-8">mongos</span>
            </EditableTableColumn>
            <EditSpecColumn
              v-model="item.spec_id"
              :bk-cloud-id="item.cluster.bk_cloud_id"
              :cluster-type="ClusterTypes.MONGODB"
              :current-spec-ids="item.cluster.mongos?.length ? [item.cluster.mongos[0].spec_config.id] : []"
              field="spec_id"
              :label="t('扩容规格')"
              :machine-type="MachineTypes.MONGOS" />
            <EditableTableColumn
              field="target_num"
              :label="t('扩容数量（台）')"
              required
              :width="300">
              <EditInput
                v-model="item.target_num"
                :min="1"
                :placeholder="t('不能少于n台', { n: 1 })"
                :rules="rules"
                type="number" />
            </EditableTableColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="tableData" />
          </EditableTableRow>
        </EditableTable>
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
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';
  import { createTicket } from '@services/source/ticket';

  import { useTicketDetail } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, MachineTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';
  import EditableTable, {
    Column as EditableTableColumn,
    Input as EditInput,
    Row as EditableTableRow,
  } from '@components/editable-table/Index.vue';

  import TicketRemark from '@views/db-manage/common/TicketRemark.vue';
  import EditSpecColumn from '@views/db-manage/common/toolbox-field/edit-spec-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import EditClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster-column/Index.vue';

  export interface IDataRow {
    cluster: {
      id?: number;
      master_domain?: string;
      mongos?: MongodbModel['mongos'];
      bk_cloud_id?: number;
    };
    spec_id?: number;
    target_num?: number;
  }

  const createRowData = (values?: Partial<IDataRow>) => ({
    cluster: values?.cluster ? values.cluster : ({} as IDataRow['cluster']),
    spec_id: values?.spec_id,
    target_num: values?.target_num,
  });

  const createDefaultFormData = () => ({
    remark: '',
  });

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  useTicketDetail<Mongodb.AddMongos>(TicketTypes.MONGODB_ADD_MONGOS, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;

      tableData.value = infos.map((infoItem) =>
        createRowData({
          cluster: {
            master_domain: clusters[infoItem.cluster_id].immute_domain,
          },
          spec_id: infoItem.resource_spec.mongos.spec_id,
          target_num: infoItem.resource_spec.mongos.count,
        }),
      );
      Object.assign(formData, {
        remark,
      });
    },
  });

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

  const isSubmitting = ref(false);
  const tableData = ref<IDataRow[]>([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => {
    const selectedClusterList = tableData.value.reduce<
      {
        id: number;
        master_domain: string;
      }[]
    >((prevList, tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id && masterDomain) {
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

    tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...newList];
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
          ticket_type: TicketTypes.MONGODB_ADD_MONGOS,
          remark: formData.remark,
          details: {
            infos: tableData.value.map((tableItem) => ({
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
        };
        await createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: TicketTypes.MONGODB_ADD_MONGOS,
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

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    tableData.value = [createRowData()];
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
