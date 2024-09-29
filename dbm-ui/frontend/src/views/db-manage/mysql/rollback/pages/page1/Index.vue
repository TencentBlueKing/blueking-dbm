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
  <BkAlert
    closable
    theme="info"
    :title="t('新建一个单节点实例_通过全备_binlog的方式_将数据库恢复到过去的某一时间点或者某个指定备份文件的状态')" />
  <div class="title-spot mt-12 mb-10">{{ t('时区') }}<span class="required" /></div>
  <TimeZonePicker style="width: 450px" />
  <div class="title-spot mt-12 mb-10">{{ t('构造类型') }}<span class="required" /></div>
  <BkRadioGroup
    v-model="rollbackClusterType"
    style="width: 450px"
    type="card"
    @change="handleChange">
    <BkRadioButton
      v-for="(value, key) in rollbackTypeLabel"
      :key="key"
      :label="key">
      {{ value }}
    </BkRadioButton>
  </BkRadioGroup>
  <RenderData
    ref="renderDataRef"
    :data="tableData"
    :rollback-cluster-type="rollbackClusterType" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useTicketCloneInfo } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import { createRowData, type IDataRow } from './components/render-row/Index.vue';
  import RenderData from './components/RenderData.vue';

  const enum RollbackClusterTypes {
    BUILD_INTO_NEW_CLUSTER = 'BUILD_INTO_NEW_CLUSTER',
    BUILD_INTO_EXIST_CLUSTER = 'BUILD_INTO_EXIST_CLUSTER',
    BUILD_INTO_METACLUSTER = 'BUILD_INTO_METACLUSTER',
  }

  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
    onSuccess(cloneData) {
      rollbackClusterType.value = cloneData.rollback_cluster_type;
      tableData.value = cloneData.tableDataList;
      window.changeConfirm = true;
    },
  });

  const rollbackTypeLabel = {
    [RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER]: t('构造到新集群'),
    [RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER]: t('构造到已有集群'),
    [RollbackClusterTypes.BUILD_INTO_METACLUSTER]: t('构造到原集群'),
  };

  const renderDataRef = ref<InstanceType<typeof RenderData>>();
  const rollbackClusterType = ref<RollbackClusterTypes>(RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER);
  const tableData = shallowRef<IDataRow[]>([createRowData({})]);

  const handleChange = () => {
    renderDataRef.value!.reset();
  };
</script>
