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
        ref="table"
        class="mt-16 mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <InstanceColumnGroup
            v-model="item.originProxy"
            :handle-row-merge="handleRowMerge"
            :rowspan="item.rowspan"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <SpecColumn
            v-model="item.specId"
            :cluster-type="DBTypes.MYSQL"
            :current-spec-id-list="[item.originProxy.spec_config.id]"
            :machine-type="MachineTypes.MYSQL_PROXY"
            required
            :rowspan="item.rowspan"
            selectable
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
  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
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

  import InstanceColumnGroup from './components/InstanceColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    originProxy: ComponentProps<typeof InstanceColumnGroup>['modelValue'];
    rowspan: number;
    specId: number;
  }

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
        city: '',
        cluster_id: 0,
        instance_address: '',
        ip: '',
        master_domain: '',
        port: 0,
        role: '',
        spec_config: {},
        subzones: '',
      } as unknown as RowData['originProxy'],
      data.originProxy,
    ),
    rowspan: data.rowspan || 1,
    specId: data.specId || 0,
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
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));
  // 具备完全相同的集群id列的行数组map
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};

  // 行合并
  const handleRowMerge = () => {
    // 接口都响应后再合并
    const isRespsoned = formData.tableData.every((item) => !!item.originProxy.cluster_id);
    if (!isRespsoned) {
      return;
    }

    formData.tableData = [..._.sortBy(formData.tableData, (item) => item.originProxy.cluster_id)];

    sameClusterIdsRowsMap = {};
    formData.tableData.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const id = item.originProxy.cluster_id;
      if (!sameClusterIdsRowsMap[id]) {
        sameClusterIdsRowsMap[id] = [item];
      } else {
        sameClusterIdsRowsMap[id].push(item);
      }
    });
    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
    });
  };

  useTicketDetail<Mysql.ResourcePool.ProxyMigrateIns>(TicketTypes.MYSQL_PROXY_MIGRATE_INS, {
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
                  instance_address: `${proxy.ip}:${proxy.port}`,
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
          port: number;
          spec: TendbhaModel['masters'][number]['spec_config'];
        }[];
      };
      origin_proxies: {
        bk_biz_id: number;
        bk_cloud_id: number;
        bk_host_id: number;
        ip: string;
        port: number;
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
  }>(TicketTypes.MYSQL_PROXY_MIGRATE_INS);

  const handleBatchEdit = (list: TendbhaInstanceModel[]) => {
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
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
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
            cluster_ids: [rows[0].originProxy.cluster_id],
            old_nodes: {
              proxy: rows.reduce<Mysql.ResourcePool.ProxyMigrateIns['infos'][0]['old_nodes']['proxy']>((acc, row) => {
                acc.push({
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: row.originProxy.bk_cloud_id,
                  bk_host_id: row.originProxy.bk_host_id,
                  ip: row.originProxy.ip,
                  port: row.originProxy.port,
                  spec: row.originProxy.spec_config,
                });
                return acc;
              }, []),
            },
            origin_proxies: rows.reduce<Mysql.ResourcePool.ProxyMigrateIns['infos'][0]['old_nodes']['proxy']>(
              (acc, row) => {
                acc.push({
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: row.originProxy.bk_cloud_id,
                  bk_host_id: row.originProxy.bk_host_id,
                  ip: row.originProxy.ip,
                  port: row.originProxy.port,
                  spec: row.originProxy.spec_config,
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
