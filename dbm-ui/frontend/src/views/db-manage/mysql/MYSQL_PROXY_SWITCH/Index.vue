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
  <ProxyWrapper>
    <SmartAction>
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumnGroup
            v-model="item.originProxy"
            :handle-row-merge="handleRowMerge"
            :rowspan="item.rowspan"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.MYSQL"
            :current-spec-id-list="item.originProxy.spec_id_list"
            :machine-type="MachineTypes.MYSQL_PROXY"
            required
            :rowspan="item.specRowspan"
            :show-tag="false"
            @batch-edit="handleBatchEditColumn" />
          <ResourceTagColumn
            v-model="item.labels"
            :rowspan="item.rowspan"
            @batch-edit="handleBatchEditColumn" />
          <AvailableResourceColumn
            :params="{
              city: item.originProxy.city,
              subzones: item.originProxy.subzones,
              for_bizs: [currentBizId, 0],
              resource_types: [DBTypes.MYSQL, 'PUBLIC'],
              spec_id: item.specId,
              labels: item.labels.map((item) => item.id).join(','),
            }"
            :rowspan="item.rowspan" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow"
            :handle-row-merge="handleRowMerge" />
        </EditableRow>
      </EditableTable>
      <BkFormItem>
        <BkCheckbox
          v-model="formData.is_safe"
          :false-label="false"
          true-label>
          <span
            v-bk-tooltips="t('存在业务连接时需要人工确认')"
            class="safe-action-text">
            {{ t('检查业务连接') }}
          </span>
        </BkCheckbox>
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
      <template #action>
        <BkButton
          class="mr-8 w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <DbPopconfirm
          :confirm-handler="handleReset"
          :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
          :title="t('确认重置页面')">
          <BkButton
            class="ml-8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </ProxyWrapper>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import ProxyWrapper from '@views/db-manage/mysql/MYSQL_PROXY_ADD/components/ProxyWrapper.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorItem } from './components/HostColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    originProxy: ComponentProps<typeof HostColumnGroup>['modelValue'];
    rowspan: number;
    specId: number;
    specRowspan: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'proxy_ip',
      label: t('目标Proxy主机'),
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
        city: '',
        ip: '',
        related_clusters: [],
        related_instances: [],
        role: '',
        spec_config: {},
        spec_id_list: [],
        subzones: '',
      } as unknown as RowData['originProxy'],
      data.originProxy,
    ),
    rowspan: data.rowspan || 1,
    specId: data.specId || 0,
    specRowspan: data.specRowspan || 1,
  });

  const defaultData = () => ({
    is_safe: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const tableKey = ref(random());
  const formData = reactive(defaultData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.originProxy.bk_host_id).map((item) => item.originProxy),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));
  // 具备完全相同的集群id列的行数组map
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};

  // 行合并
  const handleRowMerge = () => {
    // 接口都响应后再合并
    const isRespsoned = formData.tableData.every((item) => !!item.originProxy.merge_key);
    if (!isRespsoned) {
      return;
    }

    formData.tableData = [..._.sortBy(formData.tableData, (item) => item.originProxy.merge_key)];

    sameClusterIdsRowsMap = {};
    formData.tableData.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const key = item.originProxy.merge_key;
      if (!sameClusterIdsRowsMap[key]) {
        sameClusterIdsRowsMap[key] = [item];
      } else {
        sameClusterIdsRowsMap[key].push(item);
      }
    });
    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      const isSameSpecId = list.every((item) => item.specId === list[0].specId);
      Object.assign(list[0], {
        rowspan: list.length,
        specRowspan: isSameSpecId ? list.length : 1, // 同集群下所有主机都是同一规格才合并
      });
    });
  };

  const rules = {
    specId: [
      {
        message: t('主机规格不一致'),
        trigger: 'blur',
        validator: (
          value: number,
          row: {
            rowData: RowData;
            rowIndex: number;
          },
        ) => {
          const ids = (row.rowData.originProxy.related_clusters || []).map((item) => item.id).join(',');
          return sameClusterIdsRowsMap[ids].every((item) => item.specId === value);
        },
      },
    ],
  };

  useTicketDetail<Mysql.ResourcePool.ProxySwitch>(TicketTypes.MYSQL_PROXY_SWITCH, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        is_safe: details.is_safe,
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.reduce<RowData[]>((acc, item) => {
          item.old_nodes.proxy?.forEach((proxy) => {
            acc.push(
              createTableRow({
                labels: (item.resource_spec.target_proxies?.labels || []).map((item) => ({ id: Number(item) })),
                originProxy: {
                  ip: proxy.ip || '',
                },
                specId: item.resource_spec.target_proxies?.spec_id,
              }),
            );
          });
          return acc;
        }, []),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_ids: number[];
      old_nodes: {
        proxy: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          spec: TendbhaModel['masters'][number]['spec_config'];
        }[];
      };
      origin_proxies: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        spec: TendbhaModel['masters'][number]['spec_config'];
      }[];
      related_instances?: {
        cluster_id: number;
        instance_address: string;
      }[];
      resource_spec: {
        target_proxies: {
          count: number;
          label_names: string[]; // 标签名称列表，单据详情回显用
          labels: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
    is_safe: boolean;
  }>(TicketTypes.MYSQL_PROXY_SWITCH);

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
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          originProxy: {
            ip: item.proxy_ip,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          infos: Object.values(sameClusterIdsRowsMap).map((rows) => ({
            cluster_ids: rows[0].originProxy.related_clusters.map((item) => item.id),
            old_nodes: {
              proxy: rows.reduce<Mysql.ResourcePool.ProxySwitch['infos'][0]['old_nodes']['proxy']>((acc, item) => {
                acc.push({
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: item.originProxy.bk_cloud_id,
                  bk_host_id: item.originProxy.bk_host_id,
                  ip: item.originProxy.ip,
                  spec: item.originProxy.spec_config,
                });
                return acc;
              }, []),
            },
            origin_proxies: rows.reduce<Mysql.ResourcePool.ProxySwitch['infos'][0]['old_nodes']['proxy']>(
              (acc, item) => {
                acc.push({
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: item.originProxy.bk_cloud_id,
                  bk_host_id: item.originProxy.bk_host_id,
                  ip: item.originProxy.ip,
                  spec: item.originProxy.spec_config,
                });
                return acc;
              },
              [],
            ),
            resource_spec: {
              target_proxies: {
                count: rows.length,
                label_names: rows[0].labels.map((item) => item.value),
                labels: rows[0].labels.map((item) => String(item.id)),
                spec_id: rows[0].specId,
              },
            },
          })),
          ip_source: 'resource_pool',
          is_safe: formData.is_safe,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
