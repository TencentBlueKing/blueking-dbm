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
        class="mb-20 spider-layer-dr-tip"
        closable
        theme="warning"
        :title="
          t(
            '接入层灾难重建：当集群所选接入层角色（Spider Master / Spider Slave）整组不可用、无法在原机器上立即恢复时，按集群整组申请新机重建并自动下架旧机。',
          )
        " />
      <div class="mb-16">
        <div class="title-spot mt-12 mb-10">{{ t('重建对象') }}<span class="required" /></div>
        <CardCheckbox
          v-model="formData.role"
          desc="重建集群中所有的 Spider Master 节点"
          icon="host"
          :title="t('Spider Master')"
          true-value="spider_master" />
        <CardCheckbox
          v-model="formData.role"
          class="ml-8"
          desc="重建集群中所有的 Spider Slave 节点"
          icon="rebuild"
          :title="t('Spider Slave')"
          true-value="spider_slave" />
      </div>
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
          <ClusterColumn
            :ref="(el: any) => el && (clusterColumnRefs[index] = el)"
            v-model="item.cluster"
            :disable-select-config="{
              handler: (cluster: TendbClusterModel) => cluster.status === 'normal',
              tip: t('该集群状态正常，无需灾难重建'),
            }"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('当前数量（台）')"
            :min-width="150"
            readonly>
            <EditableBlock :placeholder="t('自动生成')">
              {{ item.cluster.id ? getCurrentCount(item) : '' }}
            </EditableBlock>
          </EditableColumn>
          <TargetCountColumn
            v-model="item.count"
            :max="countMax"
            :min="countMin"
            @batch-edit="handleBatchEditColumn" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="ClusterTypes.TENDBCLUSTER"
            :current-spec-id-list="
              formData.role === 'spider_slave'
                ? item.cluster.spider_slave_spec_list
                : item.cluster.spider_master_spec_list
            "
            :machine-type="MachineTypes.TENDBCLUSTER_PROXY"
            required
            selectable
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.labels"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.cluster.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { TendbCluster } from '@services/model/ticket/ticket';
  import type { ClusterListNode } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ClusterColumn from '@views/db-manage/tendb-cluster/TENDBCLUSTER_SPIDER_ADD_NODES/components/ClusterColumn.vue';

  import { random } from '@utils';

  import TargetCountColumn from './components/TargetCountColumn.vue';

  type RoleValue = 'spider_master' | 'spider_slave';

  interface RowData {
    cluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    count: string;
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');
  const clusterColumnRefs = ref<InstanceType<typeof ClusterColumn>[]>([]);
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        id: 0,
        master_domain: '',
        mnt_count: 0,
        region: '',
        spider_master: [] as TendbClusterModel['spider_master'],
        spider_master_spec_list: [] as number[],
        spider_slave: [] as TendbClusterModel['spider_slave'],
        spider_slave_spec_list: [] as number[],
      },
      data.cluster,
    ),
    count: data.count || '',
    labels: (data.labels || []) as RowData['labels'],
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    role: 'spider_master' as RoleValue,
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'spider.tendb-test.1.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: '2',
      key: 'count',
      label: t('重建后数量（台）'),
    },
    {
      case: '通用proxy配置',
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
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  // 目标数量校验范围：Master ≥ 2 不限上限；Slave [1, 10]
  const countMin = computed(() => (formData.role === 'spider_master' ? 2 : 1));
  const countMax = computed(() => (formData.role === 'spider_master' ? 0 : 10));

  const getCurrentCount = (row: RowData) =>
    formData.role === 'spider_slave' ? row.cluster.spider_slave?.length || 0 : row.cluster.spider_master?.length || 0;

  // 当行 cluster 加载完成时（id 变为非 0），如目标数量为空，则默认填为当前数量
  const autofillCount = (index: number) => {
    const row = formData.tableData[index];
    if (row && row.cluster.id && !row.count) {
      const current = getCurrentCount(row);
      if (current) {
        formData.tableData[index].count = String(current);
      }
    }
  };

  // 监听 tableData 各行 cluster.id 变化，自动回填 count
  watch(
    () => formData.tableData.map((row) => `${row.cluster.id}|${row.cluster.master_domain}`).join(','),
    () => {
      formData.tableData.forEach((_row, index) => autofillCount(index));
    },
  );

  useTicketDetail<TendbCluster.ResourcePool.SpiderLayerDr>(TicketTypes.TENDBCLUSTER_SPIDER_LAYER_DR, {
    async onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const firstInfo = details.infos[0];
      const role: RoleValue = firstInfo?.resource_spec?.spider_slave_new_ip_list ? 'spider_slave' : 'spider_master';
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        role,
        tableData: details.infos.map((item) => {
          const resourceSpec =
            role === 'spider_slave'
              ? item.resource_spec.spider_slave_new_ip_list
              : item.resource_spec.spider_master_new_ip_list;
          return createTableRow({
            cluster: {
              master_domain: details.clusters[item.cluster_id]?.immute_domain || '',
            },
            count: String(resourceSpec?.count ?? ''),
            labels: (resourceSpec?.labels || []).map((label) => ({ id: Number(label) })),
            specId: resourceSpec?.spec_id,
          });
        }),
      });
      await nextTick();
      clusterColumnRefs.value[0]?.fetchData(formData.tableData);
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: TendbCluster.ResourcePool.SpiderLayerDr['infos'];
    ip_source: 'resource_pool';
  }>(TicketTypes.TENDBCLUSTER_SPIDER_LAYER_DR);

  watch(
    () => formData.role,
    () => {
      // 切换 role 时清空表格并重置为单空行
      tableKey.value = random();
      formData.tableData = [createTableRow()];
    },
  );

  const handleSubmit = () => {
    tableRef.value!.validate().then(() => {
      const role = formData.role;
      const resourceSpecKey = role === 'spider_master' ? 'spider_master_new_ip_list' : 'spider_slave_new_ip_list';
      createTicketRun({
        details: {
          infos: formData.tableData.map((item) => {
            const oldHosts =
              role === 'spider_slave' ? item.cluster.spider_slave || [] : item.cluster.spider_master || [];
            return {
              cluster_id: item.cluster.id,
              old_nodes: {
                proxy: oldHosts.map((host: ClusterListNode) => ({
                  bk_cloud_id: host.bk_cloud_id,
                  bk_host_id: host.bk_host_id,
                  ip: host.ip,
                })),
              },
              resource_spec: {
                [resourceSpecKey]: {
                  count: Number(item.count),
                  label_names: item.labels.map((label) => label.value),
                  labels: item.labels.map((label) => String(label.id)),
                  spec_id: item.specId,
                },
              },
              strip_dns_before_install: true,
            };
          }),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
  };

  const handleBatchEdit = async (list: TendbClusterModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
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
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];

    await nextTick();
    clusterColumnRefs.value[0]?.fetchData(formData.tableData);
  };

  const handleBatchInput = async (data: Record<string, any>[], isClear: boolean) => {
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
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }

    await nextTick();
    clusterColumnRefs.value[0]?.fetchData(formData.tableData);
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
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
<style lang="less">
  .spider-layer-dr-tip.bk-alert {
    background-color: #fff7e6;
    border: 1px solid #ffd591;

    .bk-alert-icon {
      color: #ff9c01;
    }

    .bk-alert-title {
      color: #63656e;
    }
  }
</style>
