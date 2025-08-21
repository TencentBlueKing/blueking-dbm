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
    field="slaves"
    :label="t('校验从库')"
    :min-width="180"
    :loading="loading"
    required>
    <EditableSelect
      :class="{
        'mysql-checksum-select-not-empty': selected.length > 0,
      }"
      v-model="selected"
      display-key="instance_address"
      id-key="instance_address"
      :list="allSlaveInstances"
      multiple
      show-select-all
      :popover-min-width="240"
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
            class="bk-editable-text-content-placeholder ml-8">
            {{ t('请选择') }}
            <DbIcon
              size="small"
              class="angle-down render-slaves-icon"
              type="bk-dbm-icon db-icon-down-big" />
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
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="master.instance_address"
    :label="t('校验主库')"
    :min-width="180"
    required>
    <EditableBlock
      v-model="master.instance_address"
      :placeholder="t('自动生成')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { useRequest } from 'vue-request';
  import { getTendbhaInstanceList } from '@services/source/tendbha';
  import _ from 'lodash';

  type SlaveItem = ServiceReturnType<typeof getTendbhaInstanceList>['results'][0];
  type MasterItem = SlaveItem['related_pair_instance'];

  interface InstanceInfo {
    ip: string;
    port: number;
    instance_address: string;
    bk_cloud_id: number;
    bk_biz_id: number;
    bk_host_id: number;
  }

  interface RowData {
    cluster: TendbhaModel;
    table_patterns: string[];
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    master: typeof master.value;
    slaves: typeof slaves.value;
  }

  interface Props {
    cluster: TendbhaModel;
  }

  interface Emits {
    (e: 'change'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

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

  const { run: fetchData, loading } = useRequest(getTendbhaInstanceList, {
    manual: true,
    onSuccess(data) {
      allSlaveInstances.value = data.results;
      if (slaves.value.length && data.results.length > 0) {
        selected.value = slaves.value.map((item) => item.instance_address);
        return;
      }
      if (data.results.length === 1) {
        handleChange(data.results.map((item) => item.instance_address));
      }
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };

  /**
   * 以master分组映射slaves
   */
  const masterGroup = ref<Record<string, SlaveItem[]>>({});
  // 用于暂存当前选项
  let selectFinished = false;

  /**
   * 转换master数据
   */
  const generateMaster = (data: MasterItem) => ({
    ip: data.ip,
    port: data.port,
    instance_address: data.instance,
    bk_host_id: data.bk_host_id,
    bk_cloud_id: data.bk_cloud_id,
    bk_biz_id: data.bk_biz_id,
  });

  /**
   * 转换slave单项数据
   */
  const generateSlave = (data: SlaveItem) => ({
    ip: data.ip,
    port: data.port,
    instance_address: data.instance_address,
    bk_host_id: data.bk_host_id,
    bk_cloud_id: data.bk_cloud_id,
    bk_biz_id: data.bk_biz_id,
  });

  const handleChange = (values: string[]) => {
    const selectedInstances = allSlaveInstances.value.filter((item) => values.includes(item.instance_address));
    if (!selectedInstances.length) {
      slaves.value = [];
      master.value = {
        ip: '',
        port: 0,
        instance_address: '',
        bk_host_id: 0,
        bk_cloud_id: 0,
        bk_biz_id: 0,
      };
      return;
    }
    const group = _.groupBy(selectedInstances, (item) => item.related_pair_instance.instance);
    masterGroup.value = group;
    const currentMaster = generateMaster(selectedInstances[0].related_pair_instance);
    master.value = currentMaster;
    slaves.value = group[currentMaster.instance_address].map((item) => generateSlave(item));
    selectFinished = true;
  };

  // poper隐藏时再追加
  const handleToggle = () => {
    if (!selectFinished) {
      return;
    }
    const rowIndex = columnRef.value!.getRowIndex();
    const rowDataGroup = _.groupBy(tableData.value, (item) => item.master.instance_address);
    const currentRow = tableData.value[rowIndex];
    selected.value = rowDataGroup[currentRow.master.instance_address]?.[0]?.slaves.map((item) => item.instance_address);
    const newDataList: RowData[] = [];
    Object.entries(masterGroup.value).forEach(([master, slaves]) => {
      const slavesData = slaves.map((item: SlaveItem) => generateSlave(item));
      const masterRow = rowDataGroup[master]?.[0];
      if (masterRow) {
        newDataList.push(
          Object.assign({}, masterRow, {
            slaves: _.sortBy(_.uniqBy([...masterRow.slaves, ...slavesData], 'instance_address'), 'instance_address'),
            master: generateMaster(slaves[0].related_pair_instance),
          }),
        );
      } else {
        newDataList.push(
          Object.assign({}, currentRow, {
            slaves: slavesData,
            master: generateMaster(slaves[0].related_pair_instance),
          }),
        );
      }
    });
    tableData.value = newDataList;
    // 触发行合并
    emits('change');
    selectFinished = false;
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

  watch(slaves, (newList, oldList) => {
    if (newList.length !== oldList.length) {
      selected.value = slaves.value.map((item) => item.instance_address);
    }
  });
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
