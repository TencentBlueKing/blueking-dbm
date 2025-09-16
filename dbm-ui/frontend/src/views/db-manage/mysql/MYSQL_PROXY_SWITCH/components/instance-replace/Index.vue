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
    ref="table"
    class="mt-16 mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <InstanceColumnGroup
        v-model="item.originProxy"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <SpecColumn
        v-model="item.specId"
        :cluster-type="DBTypes.MYSQL"
        :current-spec-id-list="[item.originProxy.spec_config.id]"
        :machine-type="MachineTypes.MYSQL_PROXY"
        required
        selectable
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

  import { DBTypes, MachineTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';

  import { random } from '@utils';

  import InstanceColumnGroup, { type SelectorItem } from './components/InstanceColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    originProxy: ComponentProps<typeof InstanceColumnGroup>['modelValue'];
    specId: number;
  }

  interface Props {
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
            instance_address: string;
            ip: string;
            port: number;
            spec: TendbhaModel['masters'][number]['spec_config'];
          }[];
        };
        origin_proxy_ip: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          spec: TendbhaModel['masters'][number]['spec_config'];
        };
        resource_spec: {
          target_proxy: {
            count: number;
            label_names: string[]; // 标签名称列表，单据详情回显用
            labels: string[]; // 标签id列表
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

  const batchInputConfig = [
    {
      case: '192.168.10.2:10000',
      key: 'instance_address',
      label: t('目标Proxy实例'),
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
    originProxy: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_idc_city_name: '',
        bk_sub_zone: '',
        cluster_id: 0,
        instance_address: '',
        ip: '',
        master_domain: '',
        port: 0,
        role: '',
        spec_config: {},
      } as RowData['originProxy'],
      data.originProxy,
    ),
    specId: data.specId || 0,
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const tableKey = ref(random());

  const selected = computed(() =>
    tableData.value.filter((item) => item.originProxy.bk_host_id).map((item) => item.originProxy),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            const originProxy = item.old_nodes.origin_proxy?.[0];
            return createTableRow({
              labels: (item.resource_spec.target_proxy.labels || []).map((item) => ({ id: Number(item) })),
              originProxy: {
                instance_address: originProxy ? `${originProxy.ip}:${originProxy.port}` : '',
              },
              specId: item.resource_spec.target_proxy.spec_id,
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: SelectorItem[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            originProxy: {
              instance_address: item.instance_address,
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
            instance_address: item.instance_address,
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
        cluster_ids: [item.originProxy.cluster_id],
        old_nodes: {
          origin_proxy: [
            {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.originProxy.bk_cloud_id,
              bk_host_id: item.originProxy.bk_host_id,
              instance_address: item.originProxy.instance_address,
              ip: item.originProxy.ip,
              port: item.originProxy.port,
              spec: item.originProxy.spec_config,
            },
          ],
        },
        origin_proxy_ip: {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: item.originProxy.bk_cloud_id,
          bk_host_id: item.originProxy.bk_host_id,
          ip: item.originProxy.ip,
          spec: item.originProxy.spec_config,
        },
        resource_spec: {
          target_proxy: {
            count: 1,
            label_names: item.labels.map((item) => item.value),
            labels: item.labels.map((item) => String(item.id)),
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
