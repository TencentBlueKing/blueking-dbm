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
        <InstanceColumn
          v-model="item.instance"
          :cluster-types="[ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER]"
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <EditableColumn
          :label="t('所属集群')"
          :min-width="150"
          readonly>
          <EditableBlock :placeholder="t('自动生成')">
            {{ item.instance.master_domain }}
          </EditableBlock>
        </EditableColumn>
        <EditableColumn
          :label="t('角色')"
          readonly
          :width="150">
          <EditableBlock :placeholder="t('自动生成')">
            {{ item.instance.role }}
          </EditableBlock>
        </EditableColumn>
        <EditableColumn
          :label="t('状态')"
          readonly
          :width="150">
          <EditableBlock :placeholder="t('自动生成')">
            <ClusterInstanceStatus
              v-if="item.instance.bk_host_id"
              :data="item.instance.status" />
          </EditableBlock>
        </EditableColumn>
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

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { type Mongodb } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import InstanceColumn from '@views/db-manage/mongodb/common/toolbox-field/instance-column/Index.vue';

  import { ClusterTypes } from '@/common/const/clusterTypes';
  import { random } from '@/utils/random';

  interface InstanceRowData {
    instance: {
      bk_cloud_id: number;
      bk_host_id: number;
      city: string;
      cluster_id: number;
      id: number;
      instance_address: string;
      ip: string;
      master_domain: string;
      port: number;
      role: string;
      status: string;
    };
  }

  interface Exposes {
    getValue: () => Mongodb.InstanceReload['infos'];
    validate: () => Promise<boolean>;
  }

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const tableRef = useTemplateRef('tableRef');

  // 单据详情回显
  useTicketDetail<Mongodb.InstanceReload>(TicketTypes.MONGODB_INSTANCE_RELOAD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { instances, target_select_mode: targetSelectMode } = details;
      const infos = details.infos as { instance_id: number }[];

      if (targetSelectMode === 'instance') {
        tableData.value = infos.map((item) =>
          createRow({ instance: { instance_address: instances[item.instance_id].instance } }),
        );
      }
    },
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2:27017',
      key: 'instance_address',
      label: t('实例'),
    },
  ];

  const createRow = (data: DeepPartial<InstanceRowData> = {}) => ({
    instance: Object.assign(
      {
        bk_cloud_id: data.instance?.bk_cloud_id || 0,
        bk_host_id: data.instance?.bk_host_id || 0,
        city: data.instance?.city || '',
        cluster_id: data.instance?.cluster_id || 0,
        id: data.instance?.id || 0,
        instance_address: data.instance?.instance_address || '',
        ip: data.instance?.ip || '',
        master_domain: data.instance?.master_domain || '',
        port: data.instance?.port || 0,
        role: data.instance?.role || '',
        status: data.instance?.status || '',
      },
      data.instance,
    ),
  });

  const tableData = ref([createRow()]);
  const tableKey = ref(random());

  const selected = computed(() =>
    tableData.value.filter((item) => item.instance.bk_host_id).map((item) => item.instance),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const handleBatchEdit = (list: MongodbInstanceModel[]) => {
    const dataList = list.reduce<InstanceRowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(createRow({ instance: { instance_address: item.instance_address } }));
      }
      return acc;
    }, []);
    tableData.value = [...(tableData.value[0]?.instance.bk_host_id ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRow({
        instance: {
          instance_address: item.instance_address,
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

  onMounted(() => {
    if (route.query.instances) {
      tableData.value = (route.query.instances as string)
        .split(',')
        .map((item) => createRow({ instance: { instance_address: item } }));

      router.replace({ query: {} });
    }
  });

  defineExpose<Exposes>({
    getValue: () =>
      tableData.value.map((item) => ({
        bk_host_id: item.instance.bk_host_id,
        cluster_id: item.instance.cluster_id,
        instance_id: item.instance.id,
        port: item.instance.port,
        role: item.instance.role,
      })),
    validate: () => tableRef.value!.validate(),
  });
</script>
