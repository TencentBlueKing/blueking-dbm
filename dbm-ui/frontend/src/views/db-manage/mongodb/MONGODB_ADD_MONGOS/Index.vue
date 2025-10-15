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
        class="mb-16"
        closable
        theme="info"
        :title="t('扩容接入层：增加集群的Proxy数量，新Proxy可以指定规格')" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
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
              :label="t('当前数量（台）')"
              readonly
              :width="150">
              <EditableBlock> {{ item.cluster.id ? item.cluster.mongos.length : '' }}</EditableBlock>
            </EditableColumn>
            <AddProxyNumColumn
              v-model="item.add_proxy_num"
              @batch-edit="handleBatchEdit" />
            <EditableColumn
              :label="t('最终数量（台）')"
              readonly
              :width="150">
              <EditableBlock>
                {{ item.cluster.id ? item.cluster.mongos.length + item.add_proxy_num : '' }}
              </EditableBlock>
            </EditableColumn>
            <SpecColumn
              v-model="item.spec_id"
              :cluster-type="DBTypes.MONGODB"
              :current-spec-id-list="item.cluster.mongos.map((item) => item.spec_config.id)"
              field="spec_id"
              label="扩容规格"
              :machine-type="MachineTypes.MONGOS"
              required
              selectable
              @batch-edit="handleBatchEdit" />
            <ResourceTagColumn
              v-model="item.labels"
              @batch-edit="handleBatchEdit" />
            <AvailableResourceColumn
              :params="{
                city: item.cluster.region,
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MONGODB, 'PUBLIC'],
                spec_id: item.spec_id,
                labels: item.labels.map((item) => item.id).join(','),
              }" />
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

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import AddProxyNumColumn from './components/AddProxyNumColumn.vue';

  export interface IDataRow {
    add_proxy_num: number;
    cluster: {
      bk_cloud_id: number;
      cluster_type: string;
      id: number;
      master_domain: string;
      mongos: MongodbModel['mongos'];
      region: string;
    };
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    spec_id: number;
  }

  const createRowData = (values: DeepPartial<IDataRow> = {}) => ({
    add_proxy_num: values.add_proxy_num || 1,
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_type: '',
        id: 0,
        master_domain: '',
        mongos: [] as MongodbModel['mongos'],
        region: '',
      },
      values.cluster,
    ),
    labels: (values.labels || []) as IDataRow['labels'],
    spec_id: values.spec_id || 0,
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('目标分片集群'),
    },
    {
      case: '1',
      key: 'count',
      label: t('扩容数量（台）'),
    },
    {
      case: '2核_4G_50G',
      key: 'spec_name',
      label: t('扩容规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  useTicketDetail<Mongodb.AddMongos>(TicketTypes.MONGODB_ADD_MONGOS, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;

      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            add_proxy_num: infoItem.resource_spec.mongos.count,
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            labels: (infoItem.resource_spec.mongos.labels || []).map((item) => ({ id: Number(item) })),
            spec_id: infoItem.resource_spec.mongos.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      resource_spec: {
        mongos: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
      role: string;
    }[];
  }>(TicketTypes.MONGODB_ADD_MONGOS);

  const editableTableRef = useTemplateRef('editableTable');

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

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            cluster_id: tableItem.cluster.id,
            current_mongos_num: tableItem.cluster.mongos.length,
            resource_spec: {
              mongos: {
                count: tableItem.add_proxy_num,
                label_names: tableItem.labels.map((item) => item.value),
                labels: tableItem.labels.map((item) => String(item.id)),
                spec_id: tableItem.spec_id,
              },
            },
            role: 'mongos',
          })),
        },
        ...formData.payload,
      });
    }
  };

  // 批量选择
  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              id: item.id,
              master_domain: item.master_domain,
              mongos: item.mongos,
              region: item.region,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: string | string[] | number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        add_proxy_num: item.count ? Number(item.count) : 1,
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
        labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
        spec_id: item.spec_name,
      }),
    );
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
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
