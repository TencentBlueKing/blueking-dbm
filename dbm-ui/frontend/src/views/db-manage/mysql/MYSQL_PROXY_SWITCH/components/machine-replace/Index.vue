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
        v-model="item.originProxy"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <template v-if="sourceType === SourceType.RESOURCE_AUTO">
        <SpecColumn
          v-model="item.specId"
          :cluster-type="DBTypes.MYSQL"
          :current-spec-id-list="[item.originProxy.spec_id]"
          :machine-type="MachineTypes.MYSQL_PROXY"
          required
          :show-tag="false"
          @batch-edit="handleBatchEditColumn" />
        <ResourceTagColumn
          v-model="item.labels"
          @batch-edit="handleBatchEditColumn" />
        <AvailableResourceColumn
          :params="{
            city: item.originProxy.bk_idc_city_name,
            subzones: item.originProxy.bk_sub_zone,
            for_bizs: [currentBizId, 0],
            resource_types: [DBTypes.MYSQL, 'PUBLIC'],
            spec_id: item.specId,
            labels: item.labels.map((item) => item.id).join(','),
          }" />
      </template>
      <template v-if="sourceType === SourceType.RESOURCE_MANUAL">
        <SingleResourceHostColumn
          v-model="item.targetProxy"
          field="targetProxy.ip"
          :label="t('新Proxy主机')"
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

  import { DBTypes, MachineTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorItem } from './components/HostColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    originProxy: ComponentProps<typeof HostColumnGroup>['modelValue'];
    specId: number;
    targetProxy: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
  }

  interface Props {
    sourceType: SourceType;
    ticketDetails?: Mysql.ResourcePool.ProxySwitch;
  }

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_ids: number[];
        old_nodes: {
          origin_proxy: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
        };
        resource_spec: {
          target_proxy: {
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

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    labels: (data.labels || []) as RowData['labels'],
    originProxy: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_idc_city_name: '',
        bk_sub_zone: '',
        cluster_ids: [] as RowData['originProxy']['cluster_ids'],
        ip: '',
        port: 0,
        related_clusters: [] as RowData['originProxy']['related_clusters'],
        related_instances: [] as RowData['originProxy']['related_instances'],
        role: '',
        spec_id: 0,
      },
      data.originProxy,
    ),
    specId: data.specId || 0,
    targetProxy: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.targetProxy,
    ),
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const tableKey = ref(random());

  const batchInputConfig = computed(() => {
    if (props.sourceType === SourceType.RESOURCE_AUTO) {
      return [
        {
          case: '192.168.10.2',
          key: 'proxy_ip',
          label: t('目标Proxy主机'),
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
        key: 'proxy_ip',
        label: t('目标Proxy主机'),
      },
      {
        case: '192.168.10.2',
        key: 'new_proxy_ip',
        label: t('新Proxy主机'),
      },
    ];
  });

  const selected = computed(() =>
    tableData.value
      .filter((item) => item.originProxy.bk_host_id)
      .map((item) => ({
        ip: item.originProxy.ip,
      })),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));
  const targetProxyCounter = computed(() => {
    return tableData.value.reduce(
      (result, item) => {
        Object.assign(result, {
          [item.targetProxy.ip]: (result[item.targetProxy.ip] || 0) + 1,
        });
        return result;
      },
      {} as Record<string, number>,
    );
  });

  const rules = {
    'targetProxy.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: Record<string, any>) => {
          if (!value) {
            return true;
          }
          return targetProxyCounter.value[rowData.targetProxy.ip] <= 1;
        },
      },
      {
        message: t('IP 重复'),
        trigger: 'change',
        validator: (value: string, { rowData }: Record<string, any>) => {
          if (!value) {
            return true;
          }
          return targetProxyCounter.value[rowData.targetProxy.ip] <= 1;
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
              labels: (item.resource_spec.target_proxy.labels || []).map((item) => ({ id: Number(item) })),
              originProxy: {
                ip: item.old_nodes.origin_proxy?.[0]?.ip || '',
              },
              specId: item.resource_spec.target_proxy.spec_id,
              targetProxy: {
                ip: item.resource_spec.target_proxy.hosts?.[0]?.ip || '',
              },
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
            originProxy: {
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
          originProxy: {
            ip: item.proxy_ip,
          },
          specId: item.spec_name,
          targetProxy: {
            ip: item.new_proxy_ip,
          },
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
        cluster_ids: item.originProxy.cluster_ids,
        old_nodes: {
          origin_proxy: [
            {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.originProxy.bk_cloud_id,
              bk_host_id: item.originProxy.bk_host_id,
              ip: item.originProxy.ip,
              port: item.originProxy.port,
            },
          ],
        },
        resource_spec: {
          target_proxy: {
            count: 1,
            hosts: props.sourceType === SourceType.RESOURCE_MANUAL ? [item.targetProxy] : undefined,
            label_names:
              props.sourceType === SourceType.RESOURCE_AUTO ? item.labels.map((item) => item.value) : undefined,
            labels:
              props.sourceType === SourceType.RESOURCE_AUTO
                ? item.labels.filter((item) => item.id !== 0).map((item) => String(item.id))
                : undefined,
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
