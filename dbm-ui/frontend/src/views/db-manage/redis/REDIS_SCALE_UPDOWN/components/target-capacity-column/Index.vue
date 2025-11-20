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
    field="backend_group.spec_id"
    :label="t('目标容量')"
    :min-width="200"
    required
    :rule="rules">
    <div
      style="width: 100%"
      @click="handleShowSideslider">
      <EditableInput
        v-if="!modelValue.spec_id"
        :placeholder="t('请选择')">
        <template #append>
          <DbIcon
            class="down-icon"
            type="down-big" />
        </template>
      </EditableInput>
      <CapacityCell
        v-else
        :data="localTargetInfo"
        :origin-data="originTargetInfo">
        <div class="item">
          <div class="item-title">{{ t('变更方式') }}：</div>
          <div class="item-content">
            <span>{{ !modelValue.update_mode ? '--' : modelValue.update_mode === 'keep_current_machines' ? t('原地变更') : t('替换变更') }}</span>
          </div>
        </div>
      </CapacityCell>
    </div>
  </EditableColumn>
  <ClusterTargetPlan
    v-model:is-show="showClusterTargetPlan"
    :cluster="rowData.cluster"
    :db-version="rowData.db_version"
    @change="handleChangeTargetPlan" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import CapacityCell from '../CapacityCell.vue';

  import ClusterTargetPlan, { type TargetInfo, type UpdateInfo } from './cluster-deploy-plan/Index.vue';

  interface Props {
    rowData: {
      cluster: RedisModel;
      db_version: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    affinity: string;
    capacity: number;
    count: number;
    future_capacity: number;
    group_num: number;
    old_machine_info: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
    shard_num: number;
    spec_id: number;
    update_mode: string;
  }>({
    default: () => ({}),
  });

  const { t } = useI18n();

  const showClusterTargetPlan = ref(false);
  const localTargetInfo = reactive<TargetInfo>({
    capacity: 0,
    clusterShardNum: 0,
    clusterStats: { in_use: 0, total: 0, used: 0 },
    groupNum: 0,
    shardNum: 0,
    spec: {
      cpu: { max: 0, min: 0 },
      mem: { max: 0, min: 0 },
      qps: { max: 0, min: 0 },
      spec_id: 0,
      spec_name: '',
      storage_spec: undefined,
    },
  });
  const localUpdateInfo = reactive<UpdateInfo>({
    capacity_update_type: '',
    err_msg: '',
    old_machine_info: [],
    require_machine_group_num: 0,
    require_spec_id: 0,
  });

  const rules = [
    {
      message: t('请选择目标容量'),
      validator: (value: string) => Boolean(value),
    },
  ];

  const originTargetInfo = computed(() => ({
    capacity: props.rowData.cluster.cluster_capacity,
    clusterShardNum: props.rowData.cluster.cluster_shard_num,
    groupNum: props.rowData.cluster.machine_pair_cnt,
    spec: props.rowData.cluster.cluster_spec,
  }));

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'backend_group.spec_id' && !rowData.db_version) {
      return t('请先选择版本');
    }
    return '';
  };

  const handleShowSideslider = () => {
    showClusterTargetPlan.value = true;
  };

  const handleChangeTargetPlan = (payload: {
    targetInfo: typeof localTargetInfo;
    updateInfo: typeof localUpdateInfo;
  }) => {
    const { targetInfo, updateInfo } = payload;
    Object.assign(localTargetInfo, targetInfo);
    Object.assign(localUpdateInfo, updateInfo);
    modelValue.value = {
      affinity: modelValue.value.affinity,
      capacity: targetInfo.capacity || 1,
      count: updateInfo.require_machine_group_num,
      future_capacity: targetInfo.capacity || 1,
      group_num: targetInfo.groupNum,
      old_machine_info: updateInfo.old_machine_info,
      shard_num: targetInfo.clusterShardNum, // 目标集群分片数
      spec_id: targetInfo.spec.spec_id,
      update_mode: updateInfo.capacity_update_type,
    };
  };
</script>

<style lang="less" scoped>
  .down-icon {
    font-size: 15px;
    color: #979ba5;
  }
</style>
