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
    v-model="rollbackType"
    style="width: 450px"
    type="card">
    <BkRadioButton
      v-for="(item, index) in rollbackInfos"
      :key="index"
      :label="item.value">
      {{ item.label }}
    </BkRadioButton>
  </BkRadioGroup>
  <Component :is="renderCom" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  import RollbackExistCluster from './components/exist-cluster/Index.vue';
  import RollbackNewCluster from './components/new-cluster/Index.vue';
  import RollbackOriginCluster from './components/origin-cluster/Index.vue';

  const { t } = useI18n();

  enum rollbackTypes {
    ROLLBACK_NEW_CLUSTER = 'ROLLBACK_NEW_CLUSTER',
    ROLLBACK_EXIST_CLUSTER = 'ROLLBACK_EXIST_CLUSTER',
    ROLLBACK_ORIGIN_CLUSTER = 'ROLLBACK_ORIGIN_CLUSTER',
  }

  const rollbackInfos = {
    [rollbackTypes.ROLLBACK_NEW_CLUSTER]: {
      value: rollbackTypes.ROLLBACK_NEW_CLUSTER,
      label: t('构造到新集群'),
      component: RollbackNewCluster,
    },
    [rollbackTypes.ROLLBACK_EXIST_CLUSTER]: {
      value: rollbackTypes.ROLLBACK_EXIST_CLUSTER,
      label: t('构造到已有集群'),
      component: RollbackExistCluster,
    },
    [rollbackTypes.ROLLBACK_ORIGIN_CLUSTER]: {
      value: rollbackTypes.ROLLBACK_ORIGIN_CLUSTER,
      label: t('构造到原集群'),
      component: RollbackOriginCluster,
    },
  };

  const rollbackType = ref(rollbackTypes.ROLLBACK_NEW_CLUSTER);

  const renderCom = computed(() => rollbackInfos[rollbackType.value].component);
</script>
