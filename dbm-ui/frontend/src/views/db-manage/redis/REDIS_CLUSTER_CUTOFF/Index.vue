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
  <SmartAction class="redis-cluster-cutoff">
    <BkAlert
      class="mb-20"
      closable
      :title="t('整机替换：将原主机上的所有实例搬迁到同等规格的新主机')" />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <BkForm
      class="mt-16 mb-16"
      form-type="vertical"
      :model="formData">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('角色类型')"
            :min-width="150">
            <div style="flex: 1">
              <EditableBlock
                v-model="item.host.role"
                :placeholder="t('自动生成')" />
              <EditableBlock
                v-if="item.host.related_slave?.bk_host_id"
                class="related-cell">
                redis_slave
              </EditableBlock>
            </div>
          </EditableColumn>
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.host.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <SpecColumn v-model="item.host" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
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
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';
  import SpecColumn from './components/SpecColumn.vue';

  interface RowData {
    host: ComponentProps<typeof HostColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('待替换主机'),
    },
  ];

  const createTableRow = (data: { host?: Partial<RowData['host']> } = {}) => ({
    host: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_ids: [] as number[],
        ip: '',
        master_domain: '',
        role: '',
        spec_config: {} as RowData['host']['spec_config'],
      },
      data.host,
    ),
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());
  const tableKey = ref(Date.now());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Redis.ResourcePool.ClusterCutoff>(TicketTypes.REDIS_CLUSTER_CUTOFF, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
      });
      if (infos.length > 0) {
        const dataList: RowData[] = [];
        const checkMap: Record<string, boolean> = {};
        const generateData = (list: { ip: string; master_ip: string }[]) => {
          if (list?.length) {
            list.forEach((item) => {
              const ip = item.master_ip || item.ip;
              if (!checkMap[ip]) {
                dataList.push(
                  createTableRow({
                    host: {
                      ip,
                    },
                  }),
                );
                checkMap[ip] = true;
              }
            });
          }
        };
        infos.forEach((item) => {
          generateData(item.old_nodes.redis_master);
          generateData(item.old_nodes.redis_slave);
          generateData(item.old_nodes.proxy);
        });
        formData.tableData = [...dataList];
      }
    },
  });

  interface TicketDetail {
    infos: {
      bk_cloud_id: number;
      cluster_ids: number[];
      proxy: TicketDetail['infos'][0]['redis_master'];
      redis_master: {
        bk_host_id: number;
        ip: string;
        spec_id: number;
      }[];
      redis_slave: TicketDetail['infos'][0]['redis_master'];
    }[];
    ip_source: 'resource_pool';
  }

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<TicketDetail>(
    TicketTypes.REDIS_CLUSTER_CUTOFF,
  );

  const handleSubmit = async () => {
    const result = await tableRef.value!.validate();
    if (!result) {
      return;
    }
    const sameClusters = _.groupBy(formData.tableData, (item) => item.host.master_domain);

    const infos = Object.values(sameClusters).map((sameRows) => {
      const info = {
        bk_cloud_id: sameRows[0].host.bk_cloud_id,
        cluster_ids: sameRows[0].host.cluster_ids,
        proxy: [],
        redis_master: [],
        redis_slave: [],
      };
      sameRows.forEach((item) => {
        const spec = {
          bk_host_id: item.host.bk_host_id,
          ip: item.host.ip,
          spec_id: item.host.spec_config.id,
        };
        const list = info[item.host.role as 'redis_slave' | 'redis_master' | 'proxy'];
        _.merge(info, {
          [item.host.role]: [...list, spec],
        });
      });
      return info;
    });

    createTicketRun({
      details: {
        infos,
        ip_source: 'resource_pool',
      },
      ...formData.payload,
    });
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
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
          host: {
            ip: item.ip,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = Date.now();
      formData.tableData = [...dataList]; // 覆盖
    } else {
      formData.tableData = [...(formData.tableData[0].host.bk_host_id ? formData.tableData : []), ...dataList]; // 追加
    }
  };
</script>
<style lang="less">
  .redis-cluster-cutoff {
    .related-cell {
      border-top: 1px solid #dcdee5;
    }
  }
</style>
