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
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <InstanceColumnGroup
        v-model="item.originProxy"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <SingleResourceHostColumn
        v-model="item.targetProxy"
        field="targetProxy.ip"
        :label="t('新Proxy主机')"
        :params="{
          resource_types: [DBTypes.MYSQL, 'PUBLIC'],
        }" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';

  import { ProxyReplaceTypes } from '../types';

  import InstanceColumnGroup, { type SelectorItem } from './InstanceColumnGroup.vue';

  interface RowData {
    originProxy: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      cluster_id: number;
      instance_address: string;
      master_domain: string;
    };
    targetProxy: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }

  interface Props {
    data: RowData[];
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
            port?: number;
            instance_address?: string;
          }[];
        };
        resource_spec: {
          target_proxy: {
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
          };
        };
        display_info: {
          type: ProxyReplaceTypes;
          related_clusters: string[];
        };
      }[]
    >;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    originProxy: data.originProxy || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      port: 0,
      cluster_id: 0,
      instance_address: '',
      master_domain: '',
    },
    targetProxy: data.targetProxy || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() =>
    tableData.value
      .filter((item) => item.originProxy.bk_host_id)
      .map((item) => ({
        instance_address: item.originProxy.instance_address,
      })),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  watch(
    () => props.data,
    () => {
      if (props.data.length) {
        tableData.value = [...props.data];
      } else {
        tableData.value = [createTableRow()];
      }
    },
  );

  const handleBatchEdit = (list: SelectorItem[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            originProxy: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              port: item.port,
              cluster_id: item.cluster_id,
              instance_address: item.instance_address,
              master_domain: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return [];
      }

      return tableData.value.map(({ originProxy, targetProxy }) => ({
        cluster_ids: [originProxy.cluster_id],
        old_nodes: {
          origin_proxy: [
            {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: originProxy.bk_cloud_id,
              bk_host_id: originProxy.bk_host_id,
              ip: originProxy.ip,
              port: originProxy.port,
              instance_address: originProxy.instance_address,
            },
          ],
        },
        resource_spec: {
          target_proxy: {
            hosts: [
              {
                bk_biz_id: targetProxy.bk_biz_id,
                bk_cloud_id: targetProxy.bk_cloud_id,
                bk_host_id: targetProxy.bk_host_id,
                ip: targetProxy.ip,
              },
            ],
          },
        },
        display_info: {
          type: ProxyReplaceTypes.INSTANCE_REPLACE,
          related_clusters: [originProxy.master_domain],
        },
      }));
    },
  });
</script>
