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
    class="mt-16 mb-20"
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
      <template v-if="sourceType === SourceType.RESOURCE_AUTO">
        <SpecColumn
          v-model="item.specId"
          :cluster-type="DBTypes.MYSQL"
          :current-spec-id-list="item.batchCluster.spec_id_list"
          required
          selectable
          @batch-edit="handleBatchEditColumn" />
        <ResourceTagColumn
          v-model="item.labels"
          @batch-edit="handleBatchEditColumn" />
        <AvailableResourceColumn
          :params="{
            city: generateCity(item.batchCluster.clusters),
            for_bizs: [currentBizId, 0],
            resource_types: [DBTypes.MYSQL, 'PUBLIC'],
            spec_id: item.specId,
            labels: item.labels.map((item) => item.id).join(','),
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

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';

  import { random } from '@utils';

  import ClusterColumn from './components/ClusterColumn.vue';

  interface RowData {
    batchCluster: ComponentProps<typeof ClusterColumn>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
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
            label_names?: string[]; // 标签名称列表，单据详情回显用
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
            label_names?: string[]; // 标签名称列表，单据详情回显用
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

  const batchInputConfig = computed(() => {
    if (props.sourceType === SourceType.RESOURCE_AUTO) {
      return [
        {
          case: 'tendbha.test.dba.db',
          key: 'master_domain',
          label: t('目标集群'),
        },
        {
          case: '2核_4G_50G',
          key: 'spec_name',
          label: t('规格'),
        },
        {
          case: '标签1,标签2',
          key: 'labels',
          label: t('资源标签'),
        },
      ];
    }
    return [
      {
        case: 'tendbha.test.dba.db',
        key: 'master_domain',
        label: t('目标集群'),
      },
      {
        case: '192.168.10.2',
        key: 'new_master_ip',
        label: t('新Master主机'),
      },
      {
        case: '192.168.10.2',
        key: 'new_slave_ip',
        label: t('新Slave主机'),
      },
    ];
  });

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    batchCluster: Object.assign(
      {
        clusters: {} as RowData['batchCluster']['clusters'],
        renderText: '',
        spec_id_list: [] as RowData['batchCluster']['spec_id_list'],
        specId: 0,
      },
      data.batchCluster,
    ),
    labels: (data.labels || []) as RowData['labels'],
    newMaster: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.newMaster,
    ),
    newSlave: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.newSlave,
    ),
    specId: data.specId || 0,
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const tableKey = ref(random());

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
              labels: (item.resource_spec.new_master.labels || []).map((item) => ({ id: Number(item) })),
              newMaster: {
                ip: item.resource_spec.new_master.hosts?.[0]?.ip || '',
              },
              newSlave: {
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
              renderText: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...tableData.value.filter((item) => item.batchCluster.renderText), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          batchCluster: {
            renderText: item.master_domain,
          },
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          newMaster: {
            ip: item.new_master_ip,
          },
          newSlave: {
            ip: item.new_slave_ip,
          },
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...tableData.value.filter((item) => item.batchCluster.renderText), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    tableData.value.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };

  const generateCity = (clusters: Record<string, { id: number; master_domain: string; region: string }>) => {
    const cities = Object.values(clusters).map((item) => item.region);
    return cities.length ? cities.join(',') : '';
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
            label_names:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => item.value) : undefined,
            labels:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => String(item.id)) : undefined,
            spec_id: item.specId,
          },
          new_slave: {
            count: 1,
            hosts: props.sourceType === SourceType.RESOURCE_MANUAL ? [item.newSlave] : undefined,
            label_names:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => item.value) : undefined,
            labels:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => String(item.id)) : undefined,
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
