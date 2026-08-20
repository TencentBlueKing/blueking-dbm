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
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable>
      <template #title>
        <div style="white-space: pre-line">
          {{ t('空间评估：评估将源集群的DB数据合并到目标集群DB磁盘空间使用情况。') }}
          <br />
          {{
            t(
              '重要提示：（1）需要结合业务的数据合并逻辑，比如合并过程是否会产生临时数据，决策是否接受评估建议； （2）评估建议为理论预估，可能与实际情况存在差异，数据仅供参考',
            )
          }}
        </div>
      </template>
    </BkAlert>
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <DbForm
      class="mt-16 mb-16 toolbox-form"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-20 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <ClusterColumn
            v-model="item.source_cluster"
            allow-repeat
            field="source_cluster.master_domain"
            :label="t('源集群')"
            :selected="selected"
            @batch-edit="handleBatchEditCluster" />
          <DbNameColumn
            v-model="item.clone_db_list"
            check-not-exist
            :cluster-id="item.source_cluster?.id"
            field="clone_db_list"
            :label="t('克隆 DB 名')"
            required
            @batch-edit="handleBatchEdit" />
          <DbNameColumn
            v-model="item.ignore_db_list"
            :cluster-id="item.source_cluster?.id"
            field="ignore_db_list"
            :label="t('忽略 DB')"
            @batch-edit="handleBatchEdit" />
          <TargetClusterColumn v-model="item.target_clusters" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
    </DbForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
        @click="handleAssessment">
        {{ t('磁盘空间评估') }}
      </BkButton>
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset" />
    </template>
  </SmartAction>
  <Assessment
    ref="assessmentRef"
    v-model:table-data="formData.tableData" />
</template>

<script lang="ts" setup>
  import _ from 'lodash';
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import ClusterColumn from '@views/db-manage/mysql/common/toolbox-field/cluster-column/Index.vue';
  import DbNameColumn from '@views/db-manage/mysql/common/toolbox-field/db-name-column/Index.vue';

  import { random } from '@utils';

  import Assessment from './components/assessment/Index.vue';
  import TargetClusterColumn from './components/TargetClusterColumn.vue';

  interface RowData {
    clone_db_list: string[];
    ignore_db_list: string[];
    source_cluster: TendbhaModel;
    target_clusters: TendbhaModel[];
  }

  const { t } = useI18n();
  const router = useRouter();

  const tableRef = useTemplateRef('table');
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db',
      key: 'source_master_domain',
      label: t('源集群'),
    },
    {
      case: 'db1,db2,db3',
      key: 'clone_db_list',
      label: t('克隆 DB 名'),
    },
    {
      case: 'ignore_db1,ignore_db2',
      key: 'ignore_db_list',
      label: t('忽略 DB'),
    },
    {
      case: 'tendbha2.test.dba.db',
      key: 'target_master_domain',
      label: t('目标集群'),
    },
  ];

  const createTableRow = (data = {} as Partial<RowData>) => ({
    clone_db_list: data.clone_db_list || [],
    ignore_db_list: data.ignore_db_list || [],
    source_cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
      } as unknown as TendbhaModel,
      data.source_cluster,
    ),
    target_clusters: data.target_clusters || [],
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const assessmentRef = ref<InstanceType<typeof Assessment>>();

  const selected = computed(() =>
    formData.tableData.filter((item) => item.source_cluster.id).map((item) => item.source_cluster),
  );
  const selectedMap = computed(() =>
    Object.fromEntries(formData.tableData.map((cur) => [cur.source_cluster.master_domain, true])),
  );

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
    assessmentRef.value?.reset();
  };

  const handleAssessment = async () => {
    const result = await tableRef.value?.validate();
    if (!result) {
      return;
    }
    assessmentRef.value?.run();
  };

  const handleBatchEditCluster = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, cluster) => {
      if (!selectedMap.value[cluster.master_domain]) {
        acc.push(
          createTableRow({
            source_cluster: cluster,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createTableRow({
        clone_db_list: item.clone_db_list ? item.clone_db_list.split(',') : [],
        ignore_db_list: item.ignore_db_list ? item.ignore_db_list.split(',') : [],
        source_cluster: {
          master_domain: item.source_master_domain,
        } as TendbhaModel,
        target_clusters: (item.target_master_domain?.split(',') || []).map((item: string) => ({
          master_domain: item,
        })),
      }),
    );

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList];
    }

    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MysqlToolboxIndex',
      });
    },
  });
</script>
