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
      :title="t('给集群添加Proxy实例')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <div class="title-spot mt-12 mb-10">{{ t('主机选择方式') }}<span class="required" /></div>
      <BkRadioGroup
        v-model="sourceType"
        class="mb-16"
        style="width: 450px"
        type="card"
        @change="handleChangeMode">
        <BkRadioButton :label="SourceType.RESOURCE_AUTO">
          {{ t('资源池自动匹配') }}
        </BkRadioButton>
        <BkRadioButton :label="SourceType.RESOURCE_MANUAL">
          {{ t('资源池手动选择') }}
        </BkRadioButton>
      </BkRadioGroup>
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
            role="proxy"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.MYSQL"
            :current-spec-id="item.cluster.spec_id" />
          <template v-if="sourceType === SourceType.RESOURCE_AUTO">
            <ResourceTagColumn
              v-model="item.labels"
              v-model:selected="item.labelSelected" />
            <AvailableResourceColumn
              :params="{
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MYSQL, 'PUBLIC'],
                spec_id: item.specId,
                labels: item.labels.join(','),
              }" />
          </template>
          <template v-if="sourceType === SourceType.RESOURCE_MANUAL">
            <SingleResourceHostColumn
              v-model="item.newProxy"
              field="newProxy.ip"
              :label="t('新Proxy主机')"
              :min-width="150"
              :params="{
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MYSQL, 'PUBLIC'],
              }" />
          </template>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import type { _DeepPartial } from 'pinia';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';

  import { random } from '@utils';

  interface RowData {
    cluster: ComponentProps<typeof WithRelatedClustersColumn>['modelValue'];
    labels: number[];
    labelSelected: ComponentProps<typeof ResourceTagColumn>['selected'];
    newProxy: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: _DeepPartial<RowData> = {}) => ({
    cluster: {
      cluster_type: ClusterTypes.TENDBHA,
      id: 0,
      master_domain: '',
      spec_id: 0,
      ...data.cluster,
      related_clusters: [] as RowData['cluster']['related_clusters'],
    },
    labels: (data.labels as number[]) || ([] as number[]),
    labelSelected: [] as ComponentProps<typeof ResourceTagColumn>['selected'],
    newProxy: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      ...data.newProxy,
    },
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const sourceType = ref(SourceType.RESOURCE_AUTO);
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
  const newProxyCounter = computed(() => {
    return formData.tableData.reduce<Record<string, number>>((result, item) => {
      Object.assign(result, {
        [item.newProxy.ip]: (result[item.newProxy.ip] || 0) + 1,
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
    'newProxy.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newProxyCounter.value[row.newProxy.ip] <= 1;
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
          return newProxyCounter.value[row.newProxy.ip] <= 1;
        },
      },
    ],
  };

  useTicketDetail<Mysql.ResourcePool.ProxyAdd>(TicketTypes.MYSQL_PROXY_ADD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      tableKey.value = random();
      sourceType.value = details.source_type;
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          return createTableRow({
            cluster: {
              master_domain: clusters[item.cluster_ids[0]]?.immute_domain || '',
            },
            labels: (item.resource_spec.new_proxy.labels || []).map((item) => Number(item)),
            newProxy: {
              ip: item.resource_spec.new_proxy.hosts?.[0]?.ip || '',
            },
            specId: item.resource_spec.new_proxy.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      resource_spec: {
        new_proxy: {
          hosts?: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          label_values?: string[]; // 标签value列表，单据详情回显用
          labels?: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
    source_type: SourceType;
  }>(TicketTypes.MYSQL_PROXY_ADD);

  const handleChangeMode = () => {
    tableKey.value = random();
  };

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    createTicketRun({
      details: {
        infos: formData.tableData.map((item) => ({
          cluster_ids: [item.cluster.id, ...item.cluster.related_clusters.map((item) => item.id)],
          resource_spec: {
            new_proxy: {
              count: 1,
              hosts: sourceType.value === SourceType.RESOURCE_MANUAL ? [item.newProxy] : undefined,
              label_values:
                sourceType.value === SourceType.RESOURCE_AUTO
                  ? item.labelSelected.map((item) => item.value)
                  : undefined,
              labels:
                sourceType.value === SourceType.RESOURCE_AUTO ? item.labels.map((item) => String(item)) : undefined,
              spec_id: item.cluster.spec_id,
            },
          },
        })),
        ip_source: 'resource_pool',
        source_type: sourceType.value,
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
</script>
<style lang="less" scoped>
  :deep(.is-error .related-clusters) {
    background: initial;
  }
</style>
