<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
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
      :title="
        t(
          '批量下架不再使用的运维节点（spider_mnt 角色）实例。运维节点用于在不影响主集群的前提下提供独立的数据访问入口；下架后该节点上的访问能力被回收，主集群业务不受影响。',
        )
      " />
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <DbForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="formData.tableData">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <MntNodeColumn
            v-model="item.mntNode"
            :handle-row-merge="handleRowMerge"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <EditableColumn
            :label="t('所属集群')"
            :min-width="150"
            readonly
            :rowspan="item.rowspan">
            <EditableBlock
              v-model="item.mntNode.master_domain"
              :placeholder="t('自动生成')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow"
            :handle-row-merge="handleRowMerge" />
        </EditableRow>
      </EditableTable>
      <TicketPayload v-model="formData.payload" />
    </DbForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbResetButton
        class="ml-8"
        :confirm-handler="handleReset"
        :disabled="isSubmitting" />
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbClusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import type { SpiderMntDestroy } from '@services/model/ticket/details/tendbCluster/resource-pool/spiderMntDestroy';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import MntNodeColumn from './components/MntNodeColumn.vue';

  interface RowData {
    mntNode: ComponentProps<typeof MntNodeColumn>['modelValue'];
    rowspan: number;
  }

  const { t } = useI18n();
  const router = useRouter();
  const tableRef = useTemplateRef('table');

  const batchInputConfig = [
    {
      case: '192.168.10.2:3000',
      key: 'instance_address',
      label: t('运维节点'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    mntNode: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: '',
      ip: '',
      master_domain: '',
      port: 0,
      role: '',
      ...data.mntNode,
    },
    rowspan: data.rowspan || 1,
  });

  const defaultData = () => ({
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });

  const tableKey = ref(random());
  const formData = reactive(defaultData());
  const selected = computed(() =>
    formData.tableData.filter((item) => item.mntNode.bk_host_id).map((item) => item.mntNode),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));
  // 具备完全相同的集群id列的行数组map
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};

  // 行合并
  const handleRowMerge = () => {
    // 接口都响应后再合并
    const isResponsed = formData.tableData.every((item) => !!item.mntNode.cluster_id);
    if (!isResponsed) {
      return;
    }

    sameClusterIdsRowsMap = {};
    formData.tableData.forEach((item) => {
      const key = String(item.mntNode.cluster_id);
      if (!sameClusterIdsRowsMap[key]) {
        sameClusterIdsRowsMap[key] = [item];
      } else {
        sameClusterIdsRowsMap[key].push(item);
      }
    });

    // 设置 rowspan
    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      Object.assign(list[0], {
        rowspan: list.length,
      });
    });
  };

  useTicketDetail<SpiderMntDestroy>(TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.reduce<RowData[]>((acc, info) => {
          info.old_nodes.spider_ip_list.forEach((node) => {
            acc.push(
              createTableRow({
                mntNode: {
                  instance_address: `${node.ip}:${node.port}`,
                },
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
      cluster_id: number;
      old_nodes: {
        spider_ip_list: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
    }[];
    is_safe: boolean;
  }>(TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY);

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          infos: Object.values(sameClusterIdsRowsMap).map((rows) => ({
            cluster_id: rows[0].mntNode.cluster_id,
            old_nodes: {
              spider_ip_list: rows.map((row) => ({
                bk_cloud_id: row.mntNode.bk_cloud_id,
                bk_host_id: row.mntNode.bk_host_id,
                ip: row.mntNode.ip,
                port: row.mntNode.port,
              })),
            },
          })),
          is_safe: true,
        },
        remark: formData.payload.remark,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: TendbClusterInstanceModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.instance_address]) {
        acc.push(
          createTableRow({
            mntNode: {
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
          mntNode: {
            instance_address: item.instance_address,
          },
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].mntNode.bk_host_id ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'TendbclusterToolboxIndex',
      });
    },
  });
</script>
