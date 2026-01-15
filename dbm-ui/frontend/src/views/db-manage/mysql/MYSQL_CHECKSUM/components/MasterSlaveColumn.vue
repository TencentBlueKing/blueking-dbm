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
  <EditableColumn
    ref="column"
    :disabled-method="disabledMethod"
    :label="t('校验从库')"
    :loading="loading"
    :min-width="180"
    required>
    <EditableSelect
      v-model="selected"
      :class="{
        'mysql-checksum-select-not-empty': selected.length > 0,
      }"
      display-key="instance_address"
      id-key="instance_address"
      :list="allSlaveInstances"
      multiple
      :popover-min-width="240"
      show-select-all
      @change="handleChange"
      @toggle="handleToggle">
      <template #option="{ item }">
        <div class="mysql-checksum-select-option">
          <div class="option-label">{{ item.instance_address }}</div>
          <div class="option-info">{{ item.role ? item.role.split('_')[1] : '' }}</div>
        </div>
      </template>
      <template #trigger>
        <div class="mysql-checksum-select-trigger">
          <div
            v-if="selected.length === 0"
            class="mysql-checksum-placeholder ml-8">
            {{ t('请选择') }}
          </div>
          <div
            v-else
            class="render-slaves">
            <p
              v-for="instance in selected"
              :key="instance">
              {{ instance }}
            </p>
          </div>
          <DbIcon
            class="angle-down render-slaves-icon"
            size="small"
            type="bk-dbm-icon db-icon-down-big" />
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="master.instance_address"
    :label="t('校验主库')"
    :min-width="180"
    readonly
    required
    :rowspan="rowspan">
    <EditableBlock
      v-model="master.instance_address"
      :placeholder="t('自动生成')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';
  import { getTendbhaInstanceList } from '@services/source/tendbha';

  type SlaveItem = ServiceReturnType<typeof getTendbhaInstanceList>['results'][0];

  interface InstanceInfo {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    instance_address: string;
    ip: string;
    port: number;
  }

  interface RowData {
    cluster: TendbhaModel;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    master: typeof master.value;
    slaves: typeof slaves.value;
    table_patterns: string[];
  }

  interface Props {
    cluster: TendbhaModel;
    createTableRow: (data: Partial<RowData>) => RowData;
    handleRowMerge: () => void;
    rowspan: number;
  }

  const props = defineProps<Props>();

  const slaves = defineModel<InstanceInfo[]>('slaves', {
    required: true,
  });

  const master = defineModel<InstanceInfo>('master', {
    required: true,
  });

  const tableData = defineModel<RowData[]>('tableData', {
    required: true,
  });

  const { t } = useI18n();
  const columnRef = useTemplateRef('column');

  const allSlaveInstances = ref<SlaveItem[]>([]);
  const selected = ref<string[]>([]);
  const selectedInstances = ref<SlaveItem[]>([]);
  const masterSlavePair = ref<ServiceReturnType<typeof getRemoteMachineInstancePair>['instances']>({});

  const { run: fetchInstancePair } = useRequest(getRemoteMachineInstancePair, {
    manual: true,
    onSuccess(data) {
      masterSlavePair.value = data.instances;
      if (slaves.value.length) {
        handleChange(slaves.value.map((item) => item.instance_address));
        handleToggle();
        return;
      }
      // 如果只有一个从库，自动选中
      if (allSlaveInstances.value.length === 1) {
        handleChange([allSlaveInstances.value[0].instance_address]);
        handleToggle();
      }
    },
  });

  const { loading, run: fetchData } = useRequest(getTendbhaInstanceList, {
    manual: true,
    onSuccess(data) {
      allSlaveInstances.value = data.results;
      fetchInstancePair({
        bk_biz_id: props.cluster.bk_biz_id,
        instances: data.results.map((item) => item.instance_address),
      });
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };

  const handleChange = (values: string[]) => {
    const list = allSlaveInstances.value.filter((item) => values.includes(item.instance_address));
    if (!list.length) {
      slaves.value = [];
      master.value = {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        instance_address: '',
        ip: '',
        port: 0,
      };
      selected.value = [];
      return;
    }
    selected.value = values;
    selectedInstances.value = list;
  };

  // poper隐藏时再追加
  const handleToggle = async () => {
    if (!selectedInstances.value.length) {
      return;
    }

    const groupByMaster: Record<
      string,
      {
        master: RowData['master'];
        slaves: RowData['slaves'];
      }
    > = {};
    selectedInstances.value.forEach((slaveInfo) => {
      const slave = slaveInfo.instance_address;
      const masterInfo = masterSlavePair.value[slave];
      const master = masterInfo.instance;
      if (!groupByMaster[master]) {
        groupByMaster[master] = {
          master: {
            bk_biz_id: masterInfo.bk_biz_id,
            bk_cloud_id: masterInfo.bk_cloud_id,
            bk_host_id: masterInfo.bk_host_id,
            instance_address: masterInfo.instance,
            ip: masterInfo.ip,
            port: masterInfo.port,
          },
          slaves: [],
        };
      }
      groupByMaster[master].slaves.push({
        bk_biz_id: slaveInfo.bk_biz_id,
        bk_cloud_id: slaveInfo.bk_cloud_id,
        bk_host_id: slaveInfo.bk_host_id,
        instance_address: slaveInfo.instance_address,
        ip: slaveInfo.ip,
        port: slaveInfo.port,
      });
    });

    const list = Object.values(groupByMaster).map((info) => {
      return props.createTableRow({
        cluster: props.cluster,
        master: info.master,
        slaves: info.slaves,
      });
    });

    const rowIndex = columnRef.value!.getRowIndex();

    tableData.value.splice(rowIndex, 1, ...list);

    // 触发行合并
    setTimeout(() => {
      props.handleRowMerge();
      selectedInstances.value = [];
    });
  };

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        fetchData({
          cluster_id: props.cluster.id,
          role: 'backend_slave,backend_repeater',
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .mysql-checksum-select-option {
    display: flex;
    width: 100%;

    .option-label {
      flex: 1;
      width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .option-info {
      margin-left: auto;
      color: #979ba5;
    }
  }

  .mysql-checksum-select-not-empty.bk-select {
    .bk-select-trigger {
      height: initial !important;
    }
  }

  .mysql-checksum-select-trigger {
    .mysql-checksum-placeholder {
      color: #c4c6cc;
    }

    .render-slaves-icon {
      font-size: 15px !important;
    }

    .render-slaves {
      display: flex;
      padding: 4px 10px;
      flex-direction: column;

      p {
        margin: 0;
        overflow: hidden;
        line-height: 20px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
</style>
