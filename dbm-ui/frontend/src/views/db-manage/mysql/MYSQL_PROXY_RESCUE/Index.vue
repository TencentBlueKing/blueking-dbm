<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <BkAlert
        class="mb-20 proxy-rescue-tip"
        closable
        theme="warning"
        :title="
          t(
            'Proxy 灾难重建：当集群整组 Proxy 不可用、无法在原机器上立即恢复时（如大范围主机故障），按集群整组申请新机重建并自动下架旧机。',
          )
        " />
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
            :disable-select-method="
              (cluster: TendbhaModel) => (cluster.status === 'normal' ? t('该集群状态正常，无需灾难重建') : false)
            "
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
          <TargetCountColumn
            v-model="item.count"
            @batch-edit="handleBatchEditColumn" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.MYSQL"
            :current-spec-id-list="item.cluster.spec_id_list"
            :machine-type="MachineTypes.MYSQL_PROXY"
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
    </BkForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
<script lang="ts" setup>
  import _ from 'lodash';
  import { computed, reactive, ref, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/toolbox-field/with-related-clusters-column/Index.vue';

  import { random } from '@utils';

  import TargetCountColumn from './components/TargetCountColumn.vue';

  interface RowData {
    city: string;
    cluster: ComponentProps<typeof WithRelatedClustersColumn>['modelValue'];
    count: string;
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
    subzones: string;
  }

  const { t } = useI18n();
  const router = useRouter();
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
    payload: createTicketPayload(),
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
      case: '2',
      key: 'count',
      label: t('重建后数量（台）'),
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

  useTicketDetail<Mysql.ResourcePool.ProxyRescue>(TicketTypes.MYSQL_PROXY_RESCUE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      tableKey.value = random();
      Object.assign(formData, {
        ...createTicketPayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            cluster: {
              master_domain: clusters[item.cluster_id]?.immute_domain || '',
            },
            count: String(item.resource_spec.new_proxies?.count ?? ''),
            labels: (item.resource_spec.new_proxies?.labels || []).map((label) => ({ id: Number(label) })),
            specId: item.resource_spec.new_proxies?.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Mysql.ResourcePool.ProxyRescue['infos'];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_PROXY_RESCUE);

  const handleInputFinish = (item: RowData) => {
    const region = item.cluster.region;
    const subzones = item.cluster.cluster_subzones;
    Object.assign(item, {
      city: region && region !== 'default' ? region : '',
      // 默认目标数量 = 当前数量
      count: item.count || String(item.cluster.proxies?.length || ''),
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
        infos: formData.tableData.map((item) => {
          const proxies = item.cluster.proxies || [];
          return {
            auto_cleanup_old_proxies: true,
            cluster_id: item.cluster.id,
            old_nodes: {
              proxy: proxies.map((proxy) => ({
                bk_biz_id: proxy.bk_biz_id,
                bk_cloud_id: proxy.bk_cloud_id,
                bk_host_id: proxy.bk_host_id,
                ip: proxy.ip,
              })),
            },
            proxy_version: proxies[0]?.version || '',
            resource_spec: {
              new_proxies: {
                count: Number(item.count),
                label_names: item.labels.map((label) => label.value),
                labels: item.labels.map((label) => String(label.id)),
                spec_id: item.specId,
              },
            },
          };
        }),
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
          labels: (item.labels as string)?.split(',').map((label) => ({ value: label })),
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      formData.tableData = [...dataList];
      // 先设数据再延迟重置 tableKey，保证组件 refs 不被销毁
      nextTick(() => {
        tableKey.value = random();
      });
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

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
<style lang="less">
  .proxy-rescue-tip.bk-alert {
    background-color: #fff7e6;
    border: 1px solid #ffd591;

    .bk-alert-icon {
      color: #ff9c01;
    }

    .bk-alert-title {
      color: #63656e;
    }
  }

  :deep(.is-error .related-clusters) {
    background: initial;
  }
</style>
