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
      :title="t('添加运维节点：在原集群上增加运维节点实例来实现额外的数据访问，在运维节点上的操作不会影响原集群')" />
    <BkForm
      v-model="formData"
      class="mb-20"
      form-type="vertical">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableTableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <HostColumn
            ref="rowHostRef"
            v-model="item.host"
            :selected="selected"
            @batch-edit="handleBatchEdit"
            @change="(data) => handleChange(data, item, index)" />
          <Column
            :label="t('角色类型')"
            :min-width="150">
            <Block
              v-model="item.role"
              :placeholder="t('自动生成')" />
          </Column>
          <Column
            :label="t('所属集群')"
            :min-width="150"
            :rowspan="rowSpan[item.cluster.domain]">
            <Block
              v-model="item.cluster.domain"
              :placeholder="t('自动生成')" />
          </Column>
          <SpecColumn v-model="item.spec" />
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableTableRow>
      </EditableTable>
      <TicketRemark v-model="formData.remark" />
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

  import { queryMasterSlavePairs } from '@services/source/redisToolbox';

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import EditableTable, { Block, Column, Row as EditableTableRow } from '@components/editable-table/Index.vue';

  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import TicketRemark from '@views/db-manage/common/toolbox-field/ticket-remark/Index.vue';
  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  import HostColumn, { type HostInputed, type SelectorHost } from './components/HostColumn.vue';
  import SpecColumn from './components/SpecColumn.vue';

  interface RowData {
    host: {
      bk_biz_id: number;
      bk_host_id: number;
      bk_cloud_id: number;
      ip: string;
    };
    role: string;
    cluster: {
      domain: string;
      cluster_ids: number[]; // 关联集群的id集合
    };
    spec: SpecInfo;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    host: data.host || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
    role: data.role || '',
    cluster: data.cluster || {
      domain: '',
      cluster_ids: [],
    },
    spec: data.spec || ({} as SpecInfo),
  });

  const defaultData = () => ({
    tableData: [createTableRow()],
    remark: '',
  });

  const formData = reactive(defaultData());
  const rowHostRef = ref();

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));
  const rowSpan = computed(() =>
    formData.tableData.reduce<Record<string, number>>((acc, item) => {
      if (item.cluster.domain) {
        acc[item.cluster.domain] = (acc[item.cluster.domain] || 0) + 1;
      }
      return acc;
    }, {}),
  );

  const rules = {
    'host.tp': [
      {
        validator: (value: string) => selected.value.filter((item) => item.ip === value).length < 2,
        message: t('目标主机重复'),
        trigger: 'change',
      },
    ],
  };

  interface TicketDetail {
    ip_source: 'resource_pool';
    infos: {
      bk_cloud_id: number;
      cluster_ids: number[];
      redis_master: {
        ip: string;
        spec_id: number;
        bk_host_id: number;
      }[];
      redis_slave: TicketDetail['infos'][0]['redis_master'];
      proxy: TicketDetail['infos'][0]['redis_master'];
      display_info: {
        data: {
          ip: string;
          role: string;
          cluster_domain: string;
          spec_id: number;
          spec_name: string;
        }[];
      };
    }[];
  }

  const { run: createTicketRun, loading: isSubmitting } = useCreateTicket<TicketDetail>(
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
      if (!sameClusters[item.cluster.domain]) {
        sameClusters[item.cluster.domain] = [];
      }
      sameClusters[item.cluster.domain].push(item);
      item.cluster.cluster_ids.forEach((clusterId) => {
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
      acc[item.master_ip] = item.slave_ip;
      return acc;
    }, {});

    const infos = Object.values(sameClusters).map((sameRows) => {
      const info = {
        cluster_ids: sameRows[0].cluster.cluster_ids,
        bk_cloud_id: sameRows[0].host.bk_cloud_id,
        proxy: [],
        redis_master: [],
        redis_slave: [],
        display_info: {
          data: [],
        },
      } as unknown as TicketDetail['infos'][0];
      const needDeleteSlaves: string[] = [];
      sameRows.forEach((item) => {
        const spec = {
          bk_host_id: item.host.bk_host_id,
          ip: item.host.ip,
          spec_id: item.spec.id,
        };
        info.display_info.data.push({
          ip: item.host.ip,
          role: item.role,
          cluster_domain: item.cluster.domain,
          spec_id: item.spec?.id ?? 0,
          spec_name: item.spec?.name ?? '',
        });
        const list = info[
          item.role as 'redis_slave' | 'redis_master' | 'proxy'
        ] as TicketDetail['infos'][0]['redis_master'];
        _.merge(info, {
          [item.role]: [...list, spec],
        });
        if (item.role === 'redis_master') {
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

    createTicketRun(
      {
        ip_source: 'resource_pool',
        infos,
      },
      formData.remark,
    );
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
              ip: item.ip,
            },
            role: item.role,
            cluster: {
              domain: item.cluster_domain,
              cluster_ids: item.cluster_ids,
            },
            spec: item.spec_config,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  /**
   *
   * @param target 手输ip后查询到的数据
   * @param item 行数据
   * @param index 行索引
   */
  const handleChange = (target: HostInputed, item: RowData, index: number) => {
    const roleMap = {
      master: 'redis_master',
      slave: 'redis_slave',
      proxy: 'proxy',
    } as Record<string, string>;
    const row = createTableRow({
      host: {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: target.bk_cloud_id,
        bk_host_id: target.bk_host_id,
        ip: target.ip,
      },
      role: roleMap[target.role] || '',
      cluster: {
        domain: target.master_domain,
        cluster_ids: target.related_clusters.map((item) => item.id),
      },
      spec: target.spec_config,
    });
    Object.assign(item, row);

    // 输入的主机为master主机带出slave主机
    if (target.role === 'master') {
      queryMasterSlavePairs({
        cluster_id: target.cluster_id,
      }).then((data) => {
        const { slaves } = data[0];
        if (slaves) {
          formData.tableData.splice(
            index + 1,
            0,
            createTableRow({
              host: {
                bk_biz_id: slaves.bk_biz_id,
                bk_cloud_id: slaves.bk_cloud_id,
                bk_host_id: slaves.bk_host_id,
                ip: slaves.ip,
              },
              role: 'redis_slave',
              cluster: row.cluster,
              spec: row.spec,
            }),
          );
        }
      });
    }
  };
</script>
