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
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
    ref="table"
    class="mt-16 mb-16"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="item.cluster"
        :cluster-types="[clusterType]"
        :selected="selected"
        @batch-edit="handleBatchEditCluster" />
      <VariableColumn
        v-for="variableName in variableList"
        :key="variableName"
        v-model="item.vars[variableName]"
        :field="`vars.${variableName}`"
        :label="variableName" />
      <HostColumn
        v-if="showIpCloumn"
        v-model="item.authorize_ips"
        :cluster="item.cluster"
        :selected-ips="selectedIps" />
    </EditableRow>
  </EditableTable>
</template>

<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { type Mysql } from '@services/model/ticket/ticket';
  import { getDetail } from '@services/source/openarea';

  import { useTicketDetail } from '@hooks';

  import { type ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import HostColumn from './components/HostColumn.vue';
  import VariableColumn from './components/VariableColumn.vue';

  interface RowData {
    authorize_ips: string[];
    cluster: TendbhaModel;
    vars: Record<string, string>;
  }

  interface Props {
    clusterType: ClusterTypes;
    showIpCloumn: boolean;
    variableList: string[];
  }

  interface Exposes {
    getValue: () => Promise<
      {
        authorize_ips: string[];
        cluster_id: number;
        vars: Record<string, string>;
      }[]
    >;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'db1',
      key: 'fromDatabase',
      label: t('源 DB 名'),
    },
    {
      case: 'db2',
      key: 'toDatabase',
      label: t('新 DB 名'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    authorize_ips: (data.authorize_ips || []) as RowData['authorize_ips'],
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.cluster,
    ),
    vars: (data.vars || {}) as RowData['vars'],
  });

  const tableKey = ref(random());
  const tableData = ref([createTableRow()]);

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    Object.fromEntries(tableData.value.map((cur) => [cur.cluster.master_domain, true])),
  );
  const selectedIps = computed(() =>
    tableData.value.reduce<string[]>((acc, item) => {
      acc.push(...item.authorize_ips);
      return acc;
    }, []),
  );

  useTicketDetail<Mysql.OpenArea>(TicketTypes.MYSQL_OPEN_AREA, {
    async onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters } = details;

      // 获取模板详情
      const templateDetail = await getDetail({ id: details.config_id });

      // 解析器，根据范式提取变量映射关系
      const parser = (pattern: string, input: string) => {
        const regexPattern = new RegExp(pattern.replace(/{(.+?)}/g, '(?<$1>.+)'));
        return input.match(regexPattern)?.groups || {};
      };

      tableData.value = ticketDetail.details.config_data.map((item, index) => {
        // 集群信息
        const clusterInfo = clusters[item.cluster_id];

        // 变量
        const vars = item.execute_objects.reduce<Record<string, string>>((varAcc, varCur) => {
          const varItem = templateDetail.config_rules.reduce(
            (acc, cur) => ({
              ...acc,
              ...parser(cur.target_db_pattern, varCur.target_db),
            }),
            {},
          );
          return { ...varAcc, ...varItem };
        }, {});

        // 授权IP
        const authorizeIps: string[] = _.get(details, `rules_set[${index}].source_ips`, []);

        return createTableRow({
          authorize_ips: authorizeIps,
          cluster: {
            master_domain: clusterInfo.immute_domain,
          } as TendbhaModel,
          vars,
        });
      });
    },
  });

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            cluster,
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0].cluster.id ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        cluster: {
          master_domain: item.master_domain,
        } as TendbhaModel,
      }),
    );
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0].cluster.id ? tableData.value : []), ...dataList];
    }
  };

  defineExpose<Exposes>({
    async getValue() {
      const valid = await tableRef.value?.validate();
      if (!valid) {
        return Promise.reject([]);
      }
      return tableData.value.map((item) => ({
        authorize_ips: item.authorize_ips,
        cluster_id: item.cluster.id,
        vars: item.vars,
      }));
    },
  });
</script>
