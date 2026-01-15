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
    :disabled-method="disabledMethod"
    field="scope"
    :label="t('校验范围')"
    :min-width="120"
    required
    :rowspan="rowspan">
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="scopeOptions"
        :title="t('校验范围')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="scope"
      :list="scopeOptions"
      @change="handleChangeScope">
    </EditableSelect>
  </EditableColumn>
  <EditableColumn
    ref="column"
    :disabled-method="disabledMethod"
    field="slaves"
    :label="t('校验从库')"
    :loading="isSlaveLoading"
    :min-width="180"
    :readonly="scope === 'all'"
    :rules="slaveRules">
    <template #headAppend>
      <span class="required-icon" />
    </template>
    <EditableBlock>
      <div
        v-if="slaves.length === 0 && scope !== 'all'"
        class="tendbcluster-checksum-slave-default"
        @click="handleShowSelector">
        <div class="tendbcluster-checksum-placeholder">
          {{ t('请选择') }}
        </div>
        <DbIcon
          class="angle-down render-slaves-icon"
          size="small"
          type="bk-dbm-icon db-icon-down-big" />
      </div>

      <div v-if="scope === 'all'">{{ t('全部') }}</div>
      <div
        v-else
        class="tendbcluster-checksum-slave-selected"
        @click="handleShowSelector">
        <p
          v-for="instance in slaves"
          :key="instance.instance_address">
          {{ instance.instance_address }}
        </p>
        <DbIcon
          class="edit-btn"
          type="edit" />
      </div>
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="master.instance_address"
    :label="t('校验主库')"
    :loading="isMasterLoading"
    :min-width="180"
    readonly
    :rules="masterRules">
    <template #headAppend>
      <span class="required-icon" />
    </template>
    <EditableBlock :placeholder="t('自动生成')">
      <div v-if="scope === 'all'">
        {{ t('全部') }}
      </div>
      <div v-else>
        {{ master.instance_address }}
      </div>
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model="selectorSelected"
    v-model:is-show="isShowInstanceSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :data-source-map="dataSourceMap"
    @change="handleChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { checkInstance } from '@services/source/dbbase';
  import { getRemoteMachineInstancePair } from '@services/source/mysqlCluster';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';

  import { ClusterTypes, DBTypes } from '@common/const';

  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface InstanceInfo {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    instance_address: string;
    ip: string;
    port: number;
  }

  interface RowData {
    cluster: TendbClusterModel;
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    master: InstanceInfo;
    rowspan: number;
    scope: string;
    slaves: InstanceInfo[];
    table_patterns: string[];
  }

  interface Props {
    cluster: TendbClusterModel;
    createTableRow: (data: Partial<RowData>) => RowData;
    handleRowMerge: () => void;
    rowspan: number;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const scope = defineModel<string>('scope', {
    required: true,
  });

  const master = defineModel<InstanceInfo>('master', {
    required: true,
  });

  const slaves = defineModel<InstanceInfo[]>('slaves', {
    required: true,
  });

  const tableData = defineModel<RowData[]>('tableData', {
    required: true,
  });

  const { t } = useI18n();
  const columnRef = useTemplateRef('column');

  const selected = ref<string[]>([]);
  const selectorSelected = ref<{ [ClusterTypes.TENDBCLUSTER]: TendbclusterInstanceModel[] }>({
    [ClusterTypes.TENDBCLUSTER]: [],
  });
  const isShowInstanceSelector = ref(false);
  const showBatchEdit = ref(false);
  const isMasterLoading = ref(false);

  const scopeOptions = [
    {
      label: t('整个集群'),
      value: 'all',
    },
    {
      label: t('部分实例'),
      value: 'partial',
    },
  ];

  const slaveRules = [
    {
      message: t('校验从库不能为空'),
      trigger: 'change',
      validator: () => scope.value === 'all' || slaves.value.length > 0,
    },
  ];

  const masterRules = [
    {
      message: t('校验主库重复'),
      trigger: 'change',
      validator: (value: string) =>
        scope.value === 'all' || tableData.value.filter((item) => item.master.instance_address === value).length < 2,
    },
  ];

  const dataSourceMap = computed(() => ({
    [ClusterTypes.TENDBCLUSTER]: (params: ServiceParameters<typeof getTendbclusterInstanceList>) =>
      getTendbclusterInstanceList({
        ...params,
        cluster_id: props.cluster.id,
        role: 'backend_slave,backend_repeater,remote_slave,remote_repeater',
      }),
  }));

  const { loading: isSlaveLoading, run: checkExist } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      // 先赋值给选择器
      const selected = {
        [ClusterTypes.TENDBCLUSTER]: data.map((item) => ({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          instance_address: item.instance_address,
          ip: item.ip,
          port: item.port,
        })),
      } as unknown as { [ClusterTypes.TENDBCLUSTER]: TendbclusterInstanceModel[] };
      handleChange(selected);
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    emits('batch-edit', value, 'scope');
  };

  const handleShowSelector = () => {
    isShowInstanceSelector.value = true;
  };

  const handleChange = async (payload: { [ClusterTypes.TENDBCLUSTER]: TendbclusterInstanceModel[] }) => {
    const list = Object.values(payload).flatMap((item) => item);

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

    selectorSelected.value = payload;

    // 选中的从库信息, instance -> slave info
    const slaveInfo = list.reduce<Record<string, TendbclusterInstanceModel>>((acc, item) => {
      Object.assign(acc, {
        [item.instance_address]: item,
      });
      return acc;
    }, {});

    isMasterLoading.value = true;
    // 获取主从实例对信息
    const { instances } = await getRemoteMachineInstancePair({
      bk_biz_id: props.cluster.bk_biz_id,
      instances: list.map((item) => item.instance_address),
    });
    isMasterLoading.value = false;

    // 主库信息, instance -> master info
    const masterInfo: Record<string, ServiceReturnType<typeof getRemoteMachineInstancePair>['instances'][string]> = {};
    // 按主库分组, master -> [slave, slave, ...]
    const groupByMaster: Record<string, string[]> = {};
    Object.entries(instances).forEach(([slave, master]) => {
      if (!masterInfo[master.instance]) {
        masterInfo[master.instance] = master;
      }
      if (!groupByMaster[master.instance]) {
        groupByMaster[master.instance] = [];
      }
      groupByMaster[master.instance].push(slave);
    });

    const dataList = Object.values(masterInfo).map((master) =>
      props.createTableRow({
        cluster: props.cluster,
        master: {
          bk_biz_id: master.bk_biz_id,
          bk_cloud_id: master.bk_cloud_id,
          bk_host_id: master.bk_host_id,
          instance_address: master.instance,
          ip: master.ip,
          port: master.port,
        },
        scope: 'partial',
        slaves: groupByMaster[master.instance].map((slave) => {
          const info = slaveInfo[slave];
          return {
            bk_biz_id: info.bk_biz_id,
            bk_cloud_id: info.bk_cloud_id,
            bk_host_id: info.bk_host_id,
            instance_address: info.instance_address,
            ip: info.ip,
            port: info.port,
          };
        }),
      }),
    );

    const rowIndex = columnRef.value!.getRowIndex();

    tableData.value.splice(rowIndex, 1, ...dataList);

    // 触发行合并
    setTimeout(() => {
      props.handleRowMerge();
    });
  };

  const handleChangeScope = (value: string) => {
    if (value === 'all') {
      const rowIndex = columnRef.value!.getRowIndex();
      const rowspan = tableData.value[rowIndex]?.rowspan;
      if (rowspan) {
        tableData.value[rowIndex].rowspan = 1;
        tableData.value.splice(rowIndex + 1, rowspan - 1);
      }
    }
    selected.value = [];
    slaves.value = [];
    master.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      instance_address: '',
      ip: '',
      port: 0,
    };
  };

  watch(
    () => [props.cluster.id, slaves.value],
    () => {
      if (props.cluster.id && slaves.value.length && !selectorSelected.value[ClusterTypes.TENDBCLUSTER].length) {
        checkExist({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: [props.cluster.id],
          cluster_type: [ClusterTypes.TENDBCLUSTER],
          db_type: DBTypes.TENDBCLUSTER,
          instance_addresses: slaves.value.map((item) => item.instance_address),
          instance_role: ['backend_slave', 'backend_repeater', 'remote_slave', 'remote_repeater'],
        });
        return;
      }

      // 更新选择器选中的实例信息
      selectorSelected.value = {
        [ClusterTypes.TENDBCLUSTER]: slaves.value.map((item) => ({
          instance_address: item.instance_address,
        })) as TendbclusterInstanceModel[],
      };
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .batch-edit-btn {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }

  .required-icon::after {
    margin-left: 4px;
    line-height: 20px;
    color: @danger-color;
    content: '*';
  }

  .tendbcluster-checksum-slave-default {
    display: flex;
    width: 100%;
    cursor: pointer;
    align-items: center;
    justify-content: space-between;

    .tendbcluster-checksum-placeholder {
      color: #c4c6cc;
    }

    .render-slaves-icon {
      font-size: 15px;
      color: #979ba5;
    }
  }

  .tendbcluster-checksum-slave-selected {
    cursor: pointer;

    .render-slaves {
      display: flex;
      flex-direction: column;

      p {
        margin: 0;
        overflow: hidden;
        line-height: 20px;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    &:hover {
      .edit-btn {
        display: flex;
      }
    }

    .edit-btn {
      position: absolute;
      inset: 0;
      display: none;
      justify-content: center;
      align-items: center;
      background-color: rgb(250 251 253 / 45%);

      &:hover {
        color: #3a84ff;
      }
    }
  }
</style>
