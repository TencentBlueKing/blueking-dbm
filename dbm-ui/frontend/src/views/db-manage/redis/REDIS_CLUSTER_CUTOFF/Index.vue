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
  <SmartAction class="redis-cluster-cutoff">
    <BkAlert
      class="mb-20"
      closable
      :title="t('整机替换：将原主机上的所有实例搬迁到同等规格的新主机')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :selected="selected"
            @batch-edit="handleHostBatchEdit" />
          <EditableColumn
            :label="t('角色类型')"
            :min-width="150"
            readonly>
            <div style="flex: 1">
              <EditableBlock
                v-model="item.host.instance_role"
                :placeholder="t('自动生成')" />
              <EditableBlock
                v-if="item.host.related_slave?.bk_host_id"
                class="related-cell">
                redis_slave
              </EditableBlock>
            </div>
          </EditableColumn>
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150"
            readonly
            :rowspan="item.rowspan">
            <EditableBlock
              v-model="item.host.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.REDIS"
            :current-spec-id-list="[item.host.spec_config.id]"
            :machine-type="
              item.host.instance_role === 'proxy'
                ? MachineTypes.REDIS_PROXY
                : specClusterMachineMap[item.host.cluster_type]
            "
            required
            :rowspan="item.rowspan"
            selectable
            @batch-edit="handleBatchEdit" />
          <ResourceTagColumn
            v-model="item.labels"
            :rowspan="item.rowspan"
            @batch-edit="handleBatchEdit" />
          <AvailableResourceColumn
            :params="{
              city: item.host.region,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.REDIS, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }"
            :rowspan="item.rowspan" />
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
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';

  interface IDataRow {
    host: ComponentProps<typeof HostColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    rowspan: number;
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('待替换主机'),
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

  const rules = {
    'host.ip': [
      {
        message: '',
        trigger: 'change',
        validator: (value: string, { rowData, rowIndex }: { rowData: IDataRow; rowIndex: number }) => {
          if (
            formData.tableData.some(
              (tableItem, tableIndex) =>
                tableIndex !== rowIndex &&
                tableItem.host.master_domain === rowData.host.master_domain &&
                tableItem.host.instance_role !== rowData.host.instance_role,
            )
          ) {
            return t('同一集群仅允许替换一个角色');
          }
          return true;
        },
      },
    ],
  };

  const createTableRow = (values: DeepPartial<IDataRow> = {}) => ({
    host: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_ids: [] as number[],
        cluster_type: '',
        instance_role: '',
        ip: '',
        master_domain: '',
        region: '',
        spec_config: {} as IDataRow['host']['spec_config'],
      },
      values.host,
    ),
    labels: (values.labels || []) as IDataRow['labels'],
    rowspan: values?.rowspan || 1,
    specId: values?.specId || 0,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(Date.now());

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));
  const masterDomains = computed(() => formData.tableData.map((item) => item.host.master_domain));

  useTicketDetail<Redis.ResourcePool.ClusterCutoff>(TicketTypes.REDIS_CLUSTER_CUTOFF, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      const tableData = infos.flatMap((infoItem) => {
        const role = infoItem.switch_role as keyof (typeof infos)[number]['old_nodes'];
        const hosts = infoItem[role]!;
        const labels = (Object.values(infoItem.resource_spec)[0].labels || []).map((item) => ({ id: Number(item) }));
        const specId = Object.values(infoItem.resource_spec)[0].spec_id;

        return hosts.map((host) =>
          createTableRow({
            host: {
              ip: host.ip,
            },
            labels,
            specId,
          }),
        );
      });
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData,
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: Redis.ResourcePool.ClusterCutoff['infos'];
    ip_source: 'resource_pool';
  }>(TicketTypes.REDIS_CLUSTER_CUTOFF);

  const debouncedSortTableByCluster = _.debounce(() => {
    sortTableByCluster();
  }, 100);

  watch(masterDomains, () => {
    if (masterDomains) {
      debouncedSortTableByCluster();
    }
  });

  const sortTableByCluster = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    const emptyRowList: IDataRow[] = [];
    formData.tableData.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const { master_domain: domain } = item.host;
      if (!domain) {
        emptyRowList.push(item);
        return;
      }
      if (!clusterMap[domain]) {
        clusterMap[domain] = [item];
      } else {
        clusterMap[domain].push(item);
      }
    });

    const sortedList: IDataRow[] = [];
    Object.values(clusterMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
      sortedList.push(...list);
    });

    formData.tableData = [...sortedList, ...emptyRowList];
  };

  const getNodeInfo = (rowList: IDataRow[], instance_role: string) => {
    const nodes: NonNullable<Redis.ResourcePool.ClusterCutoff['infos'][number]['proxy']> = [];
    const oldNodes: NonNullable<Redis.ResourcePool.ClusterCutoff['infos'][number]['old_nodes']['proxy']> = [];

    rowList.forEach((row) => {
      const nodeItem = {
        bk_host_id: row.host.bk_host_id,
        ip: row.host.ip,
        spec_id: row.host.spec_config.id,
      };
      nodes.push(nodeItem);

      const oldNodeItem = {
        bk_host_id: row.host.bk_host_id,
        ip: row.host.ip,
        spec: row.host.spec_config,
      };
      oldNodes.push(oldNodeItem);
      if (instance_role === 'redis_master') {
        const relatedSlave = row.host.related_slave!;
        oldNodes.push({
          bk_host_id: relatedSlave.bk_host_id,
          ip: relatedSlave.ip,
          spec: relatedSlave.spec_config,
        });
      }
    });

    return {
      [instance_role]: nodes,
      old_nodes: {
        [instance_role]: oldNodes,
      },
    };
  };

  const resourceSpecInfo = (
    rowList: IDataRow[],
    role: string,
  ): NonNullable<Redis.ResourcePool.ClusterCutoff['infos'][number]['resource_spec']> => {
    const keyMap = {
      proxy: 'new_proxy',
      redis_master: 'backend_group',
    };
    const { labels, specId } = rowList[0];
    const labelNames = labels.map((item) => item.value);
    const labelIds = labels.map((item) => String(item.id));

    if (Object.keys(keyMap).includes(role)) {
      return {
        [keyMap[role as keyof typeof keyMap]]: {
          count: rowList.length,
          label_names: labelNames,
          labels: labelIds,
          spec_id: specId,
        },
      };
    }

    return rowList.reduce<
      Record<string, NonNullable<Redis.ResourcePool.ClusterCutoff['infos'][number]['resource_spec']['backend_group']>>
    >((prev, row) => {
      return Object.assign(prev, {
        [`redis_slave_${row.host.ip}`]: {
          count: 1,
          label_names: labelNames,
          labels: labelIds,
          spec_id: specId,
        },
      });
    }, {});
  };

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const sameClusters = _.groupBy(formData.tableData, (item) => item.host.master_domain);

    const infos = Object.values(sameClusters).map((sameRows) => {
      const info = {
        bk_cloud_id: sameRows[0].host.bk_cloud_id,
        cluster_ids: sameRows[0].host.cluster_ids,
        switch_role: sameRows[0].host.instance_role,
        ...getNodeInfo(sameRows, sameRows[0].host.instance_role),
        resource_spec: resourceSpecInfo(sameRows, sameRows[0].host.instance_role),
      };

      return info;
    });

    createTicketRun({
      details: {
        infos,
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleHostBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<IDataRow[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              ip: item.ip,
            } as IDataRow['host'],
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createTableRow({
          host: {
            ip: item.ip,
          },
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })) as IDataRow['labels'],
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = Date.now();
      formData.tableData = [...dataList]; // 覆盖
    } else {
      formData.tableData = [...(formData.tableData[0].host.bk_host_id ? formData.tableData : []), ...dataList]; // 追加
    }
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };
</script>
<style lang="less">
  .redis-cluster-cutoff {
    .related-cell {
      border-top: 1px solid #dcdee5;
    }
  }
</style>
