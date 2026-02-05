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
  <ProxyWrapper>
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <WithRelatedClustersColumn
            v-model="item.cluster"
            role="proxy"
            :selected="selected"
            @batch-edit="handleBatchEdit"
            @request-success="() => handleInputFinish(item)" />
          <EditableColumn
            :label="t('当前数量（台）')"
            :min-width="150"
            readonly>
            <EditableBlock :placeholder="t('自动生成')">
              {{ item.cluster.id ? item.cluster.proxies?.length : '' }}
            </EditableBlock>
          </EditableColumn>
          <AddCountColumn
            v-model="item.count"
            @batch-edit="handleBatchEditColumn" />
          <EditableColumn
            :label="t('最终数量（台）')"
            :min-width="150"
            readonly>
            <EditableBlock :placeholder="t('自动生成')">
              {{ item.cluster.id && item.count ? (item.cluster.proxies?.length || 0) + Number(item.count) : '' }}
            </EditableBlock>
          </EditableColumn>
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.MYSQL"
            :current-spec-id-list="item.cluster.spec_id_list"
            :machine-type="MachineTypes.MYSQL_PROXY"
            only-show-current-spec
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.city,
              subzones: item.subzones,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.MYSQL, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
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
            class="ml-8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </ProxyWrapper>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/toolbox-field/with-related-clusters-column/Index.vue';
  import ProxyWrapper from '@views/db-manage/mysql/MYSQL_PROXY_ADD/components/ProxyWrapper.vue';

  import { random } from '@utils';

  import AddCountColumn from './components/AddCountColumn.vue';

  interface RowData {
    city: string;
    cluster: ComponentProps<typeof WithRelatedClustersColumn>['modelValue'];
    count: string;
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
    subzones: string;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    city: data.city || '',
    cluster: Object.assign(
      {
        cluster_type: ClusterTypes.TENDBHA,
        id: 0,
        master_domain: '',
        related_clusters: [],
        spec_id_list: [],
      } as RowData['cluster'],
      data.cluster,
    ),
    count: data.count || '',
    labels: (data.labels || []) as RowData['labels'],
    specId: data.specId || 0,
    subzones: data.subzones || '',
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
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

  useTicketDetail<Mysql.ResourcePool.ProxyAdd>(TicketTypes.MYSQL_PROXY_ADD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      tableKey.value = random();
      Object.assign(formData, {
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          return createTableRow({
            cluster: {
              master_domain: clusters[item.cluster_ids[0]]?.immute_domain || '',
            },
            labels: (item.resource_spec.new_proxies?.labels || []).map((item) => ({ id: Number(item) })),
            specId: item.resource_spec.new_proxies?.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      current_proxy_num: number;
      resource_spec: {
        new_proxies: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_PROXY_ADD);

  const handleInputFinish = (item: RowData) => {
    const region = item.cluster.region;
    const subzones = item.cluster.cluster_subzones;
    Object.assign(item, {
      city: region && region !== 'default' ? region : '',
      subzones: subzones?.join(',') || '',
    });
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
          current_proxy_num: item.cluster.proxies!.length,
          resource_spec: {
            new_proxies: {
              count: Number(item.count),
              label_names: item.labels.map((item) => item.value),
              labels: item.labels.map((item) => String(item.id)),
              spec_id: item.specId,
            },
          },
        })),
        ip_source: 'resource_pool',
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

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          cluster: {
            master_domain: item.master_domain,
          },
          count: item.count,
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList]; // 追加
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: _.cloneDeep(value),
      });
    });
  };
</script>
<style lang="less" scoped>
  :deep(.is-error .related-clusters) {
    background: initial;
  }
</style>
