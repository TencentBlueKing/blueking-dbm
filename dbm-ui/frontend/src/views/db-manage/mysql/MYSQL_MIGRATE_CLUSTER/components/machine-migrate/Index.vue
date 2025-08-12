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
      <HostColumnGroup
        v-model="item.master"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <template v-if="sourceType === SourceType.RESOURCE_AUTO">
        <SpecColumn
          v-model="item.specId"
          :cluster-type="DBTypes.MYSQL"
          :current-spec-id-list="[item.master.spec_id]"
          required
          selectable
          @batch-edit="handleBatchEditColumn" />
        <ResourceTagColumn
          v-model="item.labels"
          @batch-edit="handleBatchEditColumn" />
        <AvailableResourceColumn
          :params="{
            city: item.master.bk_idc_city_name,
            subzones: item.master.bk_sub_zone,
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

  import type { Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { DBTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorItem } from './components/HostColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    master: ComponentProps<typeof HostColumnGroup>['modelValue'];
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
          case: '192.168.10.2',
          key: 'master_ip',
          label: t('目标Master主机'),
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
        case: '192.168.10.2',
        key: 'master_ip',
        label: t('目标Master主机'),
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
    labels: (data.labels || []) as RowData['labels'],
    master: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_idc_city_name: '',
        bk_sub_zone: '',
        cluster_ids: [] as number[],
        ip: '',
        port: 0,
        related_clusters: [] as string[],
        related_instances: [] as string[],
        role: '',
        spec_id: 0,
      },
      data.master,
    ),
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

  const selected = computed(() => tableData.value.filter((item) => item.master.bk_host_id).map((item) => item.master));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const newHostCounter = computed(() => {
    return tableData.value.reduce<Record<string, number>>((result, item) => {
      let masterCount = 1;
      if (item.master.ip === item.newMaster.ip) {
        masterCount += 1;
      }
      let slaveCount = masterCount;
      if (item.newMaster.ip === item.newSlave.ip) {
        slaveCount += 1;
      }
      Object.assign(result, {
        [item.master.ip]: (result[item.master.ip] || 0) + 1,
        [item.newMaster.ip]: (result[item.newMaster.ip] || 0) + masterCount,
        [item.newSlave.ip]: (result[item.newSlave.ip] || 0) + slaveCount,
      });
      return result;
    }, {});
  });

  const rules = {
    'master.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.master.ip] <= 1;
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
          return newHostCounter.value[row.master.ip] <= 1;
        },
      },
    ],
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
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            return createTableRow({
              labels: (item.resource_spec.new_master.labels || []).map((item) => ({ id: Number(item) })),
              master: {
                ip: item.old_nodes.old_master?.[0]?.ip || '',
              },
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

  const handleBatchEdit = (list: SelectorItem[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            master: {
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          master: {
            ip: item.master_ip,
          },
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
      tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
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

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return [];
      }

      return tableData.value.map((item) => ({
        cluster_ids: item.master.cluster_ids,
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
