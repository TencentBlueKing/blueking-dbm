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
        class="mb-20"
        closable
        theme="info"
        :title="t('扩容接入层：增加集群的Proxy数量，新Proxy可以指定规格')" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
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
              :cluster-types="[ClusterTypes.REDIS]"
              field="cluster.master_domain"
              :label="t('目标集群')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('架构版本')"
              readonly
              :width="180">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.cluster_type_name }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('当前数量（台）')"
              readonly
              :width="140">
              <EditableBlock :placeholder="t('选择集群后自动生成')">
                {{ item.cluster.id ? item.cluster.proxy.length : '' }}
              </EditableBlock>
            </EditableColumn>
            <AddProxyCountColumn
              v-model="item.add_proxy_count"
              @batch-edit="handleBatchEdit" />
            <EditableColumn
              :label="t('最终数量（台）')"
              readonly
              :width="150">
              <EditableBlock>
                {{ item.cluster.id ? item.cluster.proxy.length + item.add_proxy_count : '' }}
              </EditableBlock>
            </EditableColumn>
            <SpecColumn
              v-model="item.spec_id"
              :cluster-type="DBTypes.REDIS"
              :current-spec-id-list="item.cluster.proxy.map((item) => item.spec_config.id)"
              field="spec_id"
              :machine-type="MachineTypes.REDIS_PROXY"
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
                resource_types: [DBTypes.REDIS, 'PUBLIC'],
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
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { clusterRedisTypeList, ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import { type TabConfig } from '@components/cluster-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import AddProxyCountColumn from './components/AddProxyCountColumn.vue';

  interface IDataRow {
    add_proxy_count: number;
    cluster: {
      bk_cloud_id: number;
      cluster_spec: {
        id: number;
      };
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      proxy: RedisModel['proxy'];
      region: string;
    };
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    spec_id: number;
  }

  const createRowData = (values: DeepPartial<IDataRow> = {}) => ({
    add_proxy_count: values?.add_proxy_count || 0,
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_spec: {
          id: 0,
        },
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        proxy: [] as RedisModel['proxy'],
        region: '',
      },
      values.cluster,
    ),
    labels: (values.labels || []) as IDataRow['labels'],
    spec_id: values?.spec_id || 0,
  });

  const createDefaultFormData = () => ({
    payload: createTicketPayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
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
      label: t('目标规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  useTicketDetail<Redis.ResourcePool.ProxyScaleUp>(TicketTypes.REDIS_PROXY_SCALE_UP, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: infos.map((infoItem) =>
          createRowData({
            add_proxy_count: infoItem.resource_spec.proxy.count,
            cluster: {
              master_domain: clusters[infoItem.cluster_id].immute_domain,
            } as IDataRow['cluster'],
            labels: (infoItem.resource_spec.proxy.labels || []).map((item) => ({ id: Number(item) })),
            spec_id: infoItem.resource_spec.proxy.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Redis.ResourcePool.ProxyScaleUp['infos'];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_PROXY_SCALE_UP);

  const editableTableRef = useTemplateRef('editableTable');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: clusterRedisTypeList.join(','),
          ...params,
        }),
    },
  } as unknown as Record<string, TabConfig>;

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  // const getCurrentSpecIds = (proxy: IDataRow['cluster']['proxy']) => {
  //   const specIdList = (proxy || []).map((proxyItem) => proxyItem.spec_config.id);
  //   return Array.from(new Set(specIdList));
  // };

  // const specLabelFormat = ({ label, value }: { label: string; value: number }, index: number) => {
  //   const row = formData.tableData[index];
  //   const specCount = row.cluster.proxy.filter((proxyItem) => proxyItem.spec_config.id === value).length;
  //   return specCount ? `${label} ${t('((n))台', { n: specCount })}` : label;
  // };

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_spec: item.cluster_spec,
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
              proxy: item.proxy,
              region: item.region,
            },
          }),
        );
      }
    });

    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
  };

  const handleBatchEdit = (value: string | number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        add_proxy_count: item.count ? item.count : 1,
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

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => ({
            bk_cloud_id: tableItem.cluster.bk_cloud_id,
            cluster_id: tableItem.cluster.id,
            current_proxy_num: tableItem.cluster.proxy.length,
            resource_spec: {
              proxy: {
                count: tableItem.add_proxy_count,
                label_names: tableItem.labels.map((item) => item.value),
                labels: tableItem.labels.map((item) => String(item.id)),
                spec_id: tableItem.spec_id,
              },
            },
            target_proxy_count: tableItem.cluster.proxy.length + tableItem.add_proxy_count,
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
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
