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
  <SmartAction>
    <BkAlert
      class="mb-20"
      closable
      :title="t('整机替换：将原主机上的所有实例搬迁到同等规格的新主机')" />
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            v-model="item.host"
            :selected="selected"
            @append-row="handleAppendRow(item.host, index)"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('角色类型')"
            :min-width="150">
            <EditableBlock
              v-model="item.host.role"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150">
            <EditableBlock
              v-model="item.host.cluster_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <SpecColumn v-model="item.host.spec_config" />
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
          class="ml8 w-88"
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
  import { useI18n } from 'vue-i18n';

  import type { Redis } from '@services/model/ticket/ticket';
  import { queryMasterSlavePairs } from '@services/source/redisToolbox';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  import HostColumn, { type SelectorHost } from './components/HostColumn.vue';
  import SpecColumn from './components/SpecColumn.vue';

  interface RowData {
    host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_domain: string;
      cluster_ids: number[];
      ip: string;
      role: string;
      spec_config: SpecInfo;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    host: data.host || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_domain: '',
      cluster_ids: [],
      ip: '',
      role: '',
      spec_config: {} as SpecInfo,
    },
  });

  const defaultData = () => ({
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Redis.ResourcePool.ClusterCutoff>(TicketTypes.REDIS_CLUSTER_CUTOFF, {
    onSuccess(ticketDetail) {
      const { bk_biz_id: bizId, details } = ticketDetail;
      const { clusters, infos, specs } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
      });
      if (infos.length > 0) {
        const dataList: RowData[] = [];
        const generateData = (
          list: Redis.ResourcePool.ClusterCutoff['infos'][0]['old_nodes']['redis_master'],
          role: keyof Redis.ResourcePool.ClusterCutoff['infos'][0]['old_nodes'],
          clusterIds: number[],
        ) => {
          if (list?.length) {
            const clusterInfo = clusters[clusterIds[0]];
            list.forEach((item) => {
              dataList.push(
                createTableRow({
                  host: {
                    bk_biz_id: bizId,
                    bk_cloud_id: 0,
                    bk_host_id: item.bk_host_id,
                    cluster_domain: clusterInfo.immute_domain,
                    cluster_ids: clusterIds,
                    ip: item.ip,
                    role,
                    spec_config: specs[item.master_spec_id || item.spec_id],
                  },
                }),
              );
            });
          }
        };
        infos.forEach((item) => {
          generateData(item.old_nodes.redis_master, 'redis_master', item.cluster_ids);
          generateData(item.old_nodes.redis_slave, 'redis_slave', item.cluster_ids);
          generateData(item.old_nodes.proxy, 'proxy', item.cluster_ids);
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
    const sameClusters: Record<string, RowData[]> = {};
    const taskList: Promise<ServiceReturnType<typeof queryMasterSlavePairs>>[] = [];
    formData.tableData.forEach((item) => {
      if (!sameClusters[item.host.cluster_domain]) {
        sameClusters[item.host.cluster_domain] = [];
      }
      sameClusters[item.host.cluster_domain].push(item);
      item.host.cluster_ids.forEach((clusterId) => {
        taskList.push(
          queryMasterSlavePairs({
            cluster_id: clusterId,
          }),
        );
      });
    });
    const results = await Promise.all(taskList);
    // 主从映射关系
    const slaveMasterMap = _.flatten(results).reduce<Record<string, string>>((acc, item) => {
      Object.assign(acc, {
        [item.master_ip]: item.slave_ip,
      });
      return acc;
    }, {});

    const infos = Object.values(sameClusters).map((sameRows) => {
      const info = {
        bk_cloud_id: sameRows[0].host.bk_cloud_id,
        cluster_ids: sameRows[0].host.cluster_ids,
        proxy: [],
        redis_master: [],
        redis_slave: [],
      } as unknown as TicketDetail['infos'][0];
      const needDeleteSlaves: string[] = [];
      sameRows.forEach((item) => {
        const spec = {
          bk_host_id: item.host.bk_host_id,
          ip: item.host.ip,
          spec_id: item.host.spec_config?.id || 0,
        };
        const list = info[
          item.host.role as 'redis_slave' | 'redis_master' | 'proxy'
        ] as TicketDetail['infos'][0]['redis_master'];
        _.merge(info, {
          [item.host.role]: [...list, spec],
        });
        if (item.host.role === 'redis_master') {
          const deleteSlaveIp = slaveMasterMap[item.host.ip];
          if (deleteSlaveIp) {
            needDeleteSlaves.push(deleteSlaveIp);
          }
        }
      });
      // 当选择了master的时候，过滤对应的slave
      info.redis_slave = info.redis_slave.filter((item) => !needDeleteSlaves.includes(item.ip));
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
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_domain: item.cluster_domain,
              cluster_ids: item.cluster_ids,
              ip: item.ip,
              role: item.role,
              spec_config: item.spec_config,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleAppendRow = async (host: RowData['host'], index: number) => {
    const taskList = host.cluster_ids.map((clusterId) => queryMasterSlavePairs({ cluster_id: clusterId }));

    const results = await Promise.all(taskList);
    // 返回的是分片主机（可能多个重复），只取一个
    const [{ slaves }] = results.flatMap((data) => data.filter((item) => item.master_ip === host.ip));

    if (slaves) {
      formData.tableData.splice(
        index + 1,
        0,
        createTableRow({
          host: {
            bk_biz_id: slaves.bk_biz_id,
            bk_cloud_id: slaves.bk_cloud_id,
            bk_host_id: slaves.bk_host_id,
            cluster_domain: host.cluster_domain,
            cluster_ids: host.cluster_ids,
            ip: slaves.ip,
            role: 'redis_slave',
            spec_config: host.spec_config,
          },
        }),
      );
    }
  };
</script>
