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
  <EditableTable
    ref="table"
    class="mb-20"
    :model="tableData"
    :rules="rules">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="item.batchCluster"
        :selected="selected"
        :selected-map="selectedMap"
        @batch-edit="handleBatchEdit" />
      <SpecColumn
        v-model="item.specId"
        :cluster-type="DBTypes.MYSQL"
        :current-spec-id="item.batchCluster.specId"
        selectable />
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
          v-model="item.newMaster"
          field="newMaster.ip"
          :label="t('新Master主机')"
          :params="{
            for_bizs: [currentBizId, 0],
            resource_types: [DBTypes.MYSQL, 'PUBLIC'],
          }" />
        <SingleResourceHostColumn
          v-model="item.newSlave"
          field="newSlave.ip"
          :label="t('新Slave主机')"
          :params="{
            for_bizs: [currentBizId, 0],
            resource_types: [DBTypes.MYSQL, 'PUBLIC'],
          }" />
      </template>
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { DBTypes } from '@common/const';

  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    batchCluster: {
      clusters: Record<
        string,
        {
          id: number;
          master_domain: string;
        }
      >;
      renderText: string;
      specId: number;
    };
    labels: number[];
    labelSelected: ComponentProps<typeof ResourceTagColumn>['selected'];
    newMaster: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
    newSlave: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
    specId: number;
  }

  interface Props {
    sourceType: SourceType;
    ticketDetails?: Mysql.ResourcePool.MigrateCluster;
  }

  interface Exposes {
    getValue(): Promise<
      {
        cluster_ids: number[];
        resource_spec: {
          new_master: {
            count: number;
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
          new_slave: {
            count: number;
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
      }[]
    >;
    reset(): void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: Partial<RowData> = {}) => ({
    batchCluster: data.batchCluster || {
      clusters: {},
      renderText: '',
      specId: 0,
    },
    labels: (data.labels as number[]) || ([] as number[]),
    labelSelected: [] as ComponentProps<typeof ResourceTagColumn>['selected'],
    newMaster: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      ...data.newMaster,
    },
    newSlave: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      ...data.newSlave,
    },
    specId: data.specId || 0,
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() =>
    tableData.value
      .filter((item) => item.batchCluster.renderText)
      .flatMap((item) => Object.values(item.batchCluster.clusters)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const newHostCounter = computed(() => {
    return tableData.value.reduce<Record<string, number>>((result, item) => {
      let count = 1;
      if (item.newMaster.ip === item.newSlave.ip) {
        count += 1;
      }
      Object.assign(result, {
        [item.newMaster.ip]: (result[item.newMaster.ip] || 0) + 1,
        [item.newSlave.ip]: (result[item.newSlave.ip] || 0) + count,
      });
      return result;
    }, {});
  });

  const rules = {
    'newMaster.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.newMaster.ip] <= 1;
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
          return newHostCounter.value[row.newMaster.ip] <= 1;
        },
      },
    ],
    'newSlave.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.newSlave.ip] <= 1;
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
          return newHostCounter.value[row.newSlave.ip] <= 1;
        },
      },
    ],
  };

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            const batchCluster = {
              clusters: {},
              renderText: '',
            } as RowData['batchCluster'];
            item.cluster_ids.forEach((clusterId) => {
              batchCluster.renderText += batchCluster.renderText ? '\n' : '' + clusters[clusterId].immute_domain;
              batchCluster.clusters = Object.assign(batchCluster.clusters, {
                [clusters[clusterId].immute_domain]: {
                  id: clusters[clusterId].id,
                  master_domain: clusters[clusterId].immute_domain,
                },
              });
            });
            return createTableRow({
              batchCluster,
              labels: (item.resource_spec.new_master.labels || []).map((label) => Number(label)),
              newMaster: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: 0,
                bk_host_id: 0,
                ip: item.resource_spec.new_master.hosts?.[0]?.ip || '',
              },
              newSlave: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: 0,
                bk_host_id: 0,
                ip: item.resource_spec.new_slave.hosts?.[0]?.ip || '',
              },
              specId: item.resource_spec.new_master.spec_id,
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            batchCluster: {
              clusters: {
                [item.master_domain]: {
                  id: item.id,
                  master_domain: item.master_domain,
                },
              },
              renderText: item.master_domain,
              specId: item.cluster_spec?.spec_id || item.masters?.[0]?.spec_config.id || -1,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...tableData.value.filter((item) => item.batchCluster.renderText), ...dataList];
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return [];
      }

      return tableData.value.map((item) => ({
        cluster_ids: Object.values(item.batchCluster.clusters).map((item) => item.id),
        resource_spec: {
          new_master: {
            count: 1,
            hosts: props.sourceType === SourceType.RESOURCE_MANUAL ? [item.newMaster] : undefined,
            label_values:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labelSelected.map((item) => item.value) : undefined,
            labels: props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => String(item)) : undefined,
            spec_id: item.specId,
          },
          new_slave: {
            count: 1,
            hosts: props.sourceType === SourceType.RESOURCE_MANUAL ? [item.newSlave] : undefined,
            label_values:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labelSelected.map((item) => item.value) : undefined,
            labels: props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => String(item)) : undefined,
            spec_id: item.specId,
          },
        },
      }));
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
