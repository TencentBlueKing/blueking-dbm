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
  <div>
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <EditableTable
      :key="tableKey"
      ref="tableRef"
      class="mt-16 mb-20"
      :model="tableData">
      <EditableRow
        v-for="(item, index) in tableData"
        :key="index">
        <HostColumn
          v-model="item.host"
          :cluster-types="[ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER]"
          :columns="['cluster']"
          :label="t('主机 IP')"
          :selected="selected"
          :tab-list-config="tabListConfig"
          @batch-edit="handleBatchEdit" />
        <OperationColumn
          v-model:table-data="tableData"
          :create-row-method="createRow" />
      </EditableRow>
    </EditableTable>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { type Mongodb } from '@services/model/ticket/ticket';
  import { checkInstance } from '@services/source/dbbase';
  import { getMongodbMachineList } from '@services/source/mongodb';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes } from '@common/const';
  import { TicketTypes } from '@common/const/ticketTypes.ts';

  import { type PanelListType } from '@components/instance-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import HostColumn, { type SelectorHost } from '@views/db-manage/mongodb/common/toolbox-field/host-column/Index.vue';

  import { random } from '@utils';

  interface MachineRowData {
    host: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      related_clusters: ServiceReturnType<typeof checkInstance>[number]['related_clusters'];
      related_instances: ServiceReturnType<typeof checkInstance>;
      role: string;
      spec_config: Record<string, any>;
    };
  }

  interface Exposes {
    getValue: () => Mongodb.InstanceReload['infos'];
    validate: () => Promise<boolean>;
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('tableRef');

  // 单据详情回显
  useTicketDetail<Mongodb.InstanceReload>(TicketTypes.MONGODB_INSTANCE_RELOAD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { target_select_mode: targetSelectMode } = details;
      const infos = details.infos as { ip: string }[];

      if (targetSelectMode === 'machine') {
        tableData.value = infos.map((item) => createRow({ host: { ip: item.ip } }));
      }
    },
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('主机IP'),
    },
  ];

  const createRow = (data: DeepPartial<MachineRowData> = {}) => ({
    host: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
        related_clusters: [] as ServiceReturnType<typeof checkInstance>[number]['related_clusters'],
        related_instances: [] as ServiceReturnType<typeof checkInstance>,
        role: '',
        spec_config: {} as Record<string, any>,
      },
      data.host,
    ),
  });

  const tabListConfig = {
    mongoCluster: [
      {
        id: 'mongoCluster',
        name: t('目标主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('主机 IP'),
          },
          getTableList: (params: ServiceParameters<typeof getMongodbMachineList>) => getMongodbMachineList(params),
          multiple: true,
        },
      },
    ],
  } as Record<string, PanelListType>;

  const tableData = ref([createRow()]);
  const tableKey = ref(random());

  const selected = computed(() => tableData.value.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<MachineRowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(createRow({ host: { ip: item.ip } }));
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0]?.host.bk_host_id ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRow({
        host: {
          ip: item.ip,
        },
      }),
    );

    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
    }
  };

  defineExpose<Exposes>({
    getValue: () =>
      tableData.value.map((item) => ({
        bk_host_id: item.host.bk_host_id,
        ip: item.host.ip,
        related_clusters: item.host.related_clusters.map((item) => item.master_domain),
      })),
    validate: () => tableRef.value!.validate(),
  });
</script>
