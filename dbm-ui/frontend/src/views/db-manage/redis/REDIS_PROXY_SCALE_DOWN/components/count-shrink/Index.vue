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
  <BatchInput
    class="mb-16"
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
    ref="table"
    class="mb-20"
    :model="tableData"
    :rules="rules">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="item.cluster"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <EditableColumn
        field="cluster.cluster_type_name"
        :label="t('架构版本')"
        :min-width="150"
        readonly>
        <EditableBlock
          v-model="item.cluster.cluster_type_name"
          :placeholder="t('自动生成')" />
      </EditableColumn>
      <EditableColumn
        field="cluster.proxyCount"
        :label="t('当前数量（台）')"
        :min-width="200"
        readonly>
        <EditableBlock :placeholder="t('自动生成')">
          {{ item.cluster.id ? item.cluster.proxy.length : '' }}
        </EditableBlock>
      </EditableColumn>
      <ReducedCountColumn
        v-model="item.reduced_count"
        :cluster="item.cluster"
        :max="item.cluster.proxy.length"
        @batch-edit="handleRedecedCountBatchEdit"
        @change="handleChange(item)" />
      <EditableColumn
        :append-rules="targetCountRules"
        field="target_proxy_count"
        :label="t('剩余数量（台）')"
        :min-width="200"
        readonly>
        <EditableBlock :placeholder="t('自动生成')">
          {{
            item.target_proxy_count
              ? item.target_proxy_count
              : item.cluster.id
                ? item.cluster.proxy.length - (Number(item.reduced_count) || 0)
                : ''
          }}
        </EditableBlock>
      </EditableColumn>
      <OnlineSwitchTypeColumn
        v-model="item.online_switch_type"
        :rowspan="1"
        @batch-edit="handleOnlineSwitchTypeBatchEdit" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import type { Redis } from '@services/model/ticket/ticket';

  import { ClusterTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import OnlineSwitchTypeColumn, { ONLINE_SWITCH_TYPE } from '../OnlineSwitchTypeColumn.vue';

  import ReducedCountColumn from './components/ReducedCountColumn.vue';

  interface RowData {
    cluster: {
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      proxy: RedisModel['proxy'];
    };
    online_switch_type: string;
    reduced_count: string;
    target_proxy_count: string;
  }

  interface Props {
    ticketDetails?: Redis.ProxyScaleDown;
  }

  interface Exposes {
    getValue: () => Promise<{
      infos: {
        cluster_id: number;
        online_switch_type: string;
        target_proxy_count: number;
      }[];
    }>;
    reset: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db',
      key: 'cluster',
      label: t('源集群'),
    },
    {
      case: '1',
      key: 'reduced_count',
      label: t('缩容数量'),
    },
    {
      case: t('需人工确认'),
      key: 'online_switch_type',
      label: t('切换方式'),
      values: [t('需人工确认'), t('无需确认')],
    },
  ];

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        proxy: [],
      },
      data.cluster,
    ),
    online_switch_type: data.online_switch_type || ONLINE_SWITCH_TYPE.USER_CONFIRM,
    reduced_count: data.reduced_count || '',
    target_proxy_count: data.target_proxy_count || '',
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(tableData.value.map((cur) => [cur.cluster.master_domain, true])),
  );

  const rules = {
    'cluster.master_domain': [
      {
        message: t('数量不足，Proxy至少保留 2 台'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          return !value || rowData.cluster.proxy.length >= 2;
        },
      },
    ],
  };

  const targetCountRules = [
    {
      message: t('剩余数量必须大于等于2'),
      trigger: 'change',
      validator: (value: string) => Number(value) >= 2,
    },
  ];

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            return createTableRow({
              // 集群缺失信息会被ClusterColumn组件会填
              cluster: {
                master_domain: clusters[item.cluster_id].immute_domain,
              },
              online_switch_type: item.online_switch_type,
              reduced_count: `${item.old_nodes.proxy_reduced_hosts.length}`,
              target_proxy_count: `${item.target_proxy_count}`,
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: RedisModel[]) => {
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
    tableData.value = [...(tableData.value[0].cluster.id ? tableData.value : []), ...dataList];
  };

  const handleRedecedCountBatchEdit = (value: string | string[]) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        reduced_count: value,
      });
      handleChange(item);
    });
  };

  const handleOnlineSwitchTypeBatchEdit = (value: string | string[]) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        online_switch_type: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) => {
      const rowData = createTableRow({
        online_switch_type: item.online_switch_type,
        reduced_count: item.reduced_count,
      });
      if (item.cluster) {
        rowData.cluster.master_domain = item.cluster;
      }
      return rowData;
    });
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0].cluster.id ? tableData.value : []), ...dataList];
    }
  };

  const handleChange = (row: RowData) => {
    Object.assign(row, {
      target_proxy_count: row.cluster.proxy.length - (Number(row.reduced_count) || 0),
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return {
          infos: [],
        };
      }

      return {
        infos: tableData.value.map((item) => ({
          cluster_id: item.cluster.id,
          online_switch_type: item.online_switch_type,
          target_proxy_count: Number(item.target_proxy_count),
        })),
      };
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
