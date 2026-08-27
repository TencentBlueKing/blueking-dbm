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
  <BkFormItem
    :label="t('迁移内容')"
    required>
    <BkRadioGroup
      v-model="formData.orphan_restore_type"
      @change="handleChange">
      <BkRadio label="replicate_with_data">
        {{ t('包含数据+实时同步') }}
      </BkRadio>
      <BkRadio label="replicate_with_struct">
        {{ t('仅表结构+实时同步') }}
      </BkRadio>
      <BkRadio label="restore_from_flow_backup">
        {{ t('仅表结构(本地实时导出)') }}
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
  <BkFormItem
    v-if="formData.orphan_restore_type !== 'restore_from_flow_backup'"
    :label="t('备份源')"
    required>
    <BkRadioGroup v-model="formData.backup_source">
      <BkRadio :label="BackupSourceType.LOCAL">
        {{ t('本地备份') }}
      </BkRadio>
      <BkRadio :label="BackupSourceType.REMOTE">
        {{ t('远程备份') }}
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
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
      <MultipleClusterColumn
        v-model="item.multipleCluster"
        :cluster-types="[ClusterTypes.TENDBSINGLE]"
        :selected="selected"
        :selected-map="selectedMap"
        @batch-edit="handleBatchEditCluster" />
      <SpecColumn
        v-model="item.specId"
        :cluster-type="DBTypes.MYSQL"
        :current-spec-id-list="item.multipleCluster.spec_ids"
        required
        selectable
        @batch-edit="handleBatchEdit" />
      <ResourceTagColumn
        v-model="item.labels"
        @batch-edit="handleBatchEdit" />
      <AvailableResourceColumn
        :params="{
          subzones: item.multipleCluster.subzones,
          city: item.multipleCluster.city,
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
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { type Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import MultipleClusterColumn from '@views/db-manage/mysql/common/toolbox-field/multiple-cluster-column/Index.vue';

  import { random } from '@utils';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    multipleCluster: ComponentProps<typeof MultipleClusterColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: 'tendbha.test.dba.db\\ntendbha.test2.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
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

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    labels: (data.labels || []) as RowData['labels'],
    multipleCluster: Object.assign(
      {
        city: '',
        clusters: [],
        renderText: '',
        spec_ids: [],
        subzones: '',
      } as RowData['multipleCluster'],
      data.multipleCluster,
    ),
    specId: data.specId || 0,
  });

  const formData = reactive({
    backup_source: BackupSourceType.REMOTE,
    orphan_restore_type: 'replicate_with_data',
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });
  const tableKey = ref(random());

  const selected = computed(() =>
    formData.tableData
      .filter((item) => item.multipleCluster.renderText)
      .flatMap((item) => Object.values(item.multipleCluster.clusters)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  useTicketDetail<Mysql.ResourcePool.MigrateSingle>(TicketTypes.MYSQL_MIGRATE_SINGLE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      if (details.migrate_type !== 'instance') {
        return;
      }
      const { clusters } = details;
      Object.assign(formData, {
        backup_source: details.backup_source,
        orphan_restore_type: details.orphan_restore_type,
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            labels: (item.resource_spec.bk_new_orphan?.labels || []).map((item) => ({ id: Number(item) })),
            multipleCluster: {
              renderText: item.cluster_ids.map((clusterId) => clusters[clusterId]?.immute_domain).join('\n'),
            },
            specId: item.resource_spec.bk_new_orphan?.spec_id || 0,
          }),
        ),
      });
    },
  });

  const handleChange = (value: string) => {
    formData.orphan_restore_type = value;
    formData.backup_source = BackupSourceType.LOCAL;
  };

  const handleBatchEditCluster = (list: TendbsingleModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            multipleCluster: {
              renderText: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...formData.tableData.filter((item) => item.multipleCluster.renderText), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          multipleCluster: {
            renderText: item.master_domain?.replaceAll('\\n', '\n') || '',
          },
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...formData.tableData.filter((item) => item.multipleCluster.renderText), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose({
    getValue() {
      return tableRef.value!.validate().then(() => {
        return {
          details: {
            backup_source: formData.backup_source,
            infos: formData.tableData.map((item) => {
              const clusters = item.multipleCluster.clusters;
              return {
                cluster_ids: clusters.map((cluster) => cluster.id),
                old_orphan: {
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: clusters[0].masters[0].bk_cloud_id,
                  bk_host_id: clusters[0].masters[0].bk_host_id,
                  ip: clusters[0].masters[0].ip,
                },
                resource_spec: {
                  bk_new_orphan: {
                    count: 1,
                    label_names: item.labels.map((item) => item.value),
                    labels: item.labels.map((item) => String(item.id)),
                    spec_id: item.specId,
                  },
                },
              };
            }),
            ip_source: 'resource_pool',
            migrate_type: 'instance',
            orphan_restore_type: formData.orphan_restore_type,
          },
          ...formData.payload,
        };
      });
    },
  });
</script>
