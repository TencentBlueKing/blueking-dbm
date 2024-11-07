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
  <div class="redis-migrate">
    <BkAlert
      closable
      theme="info"
      :title="
        t(
          '集群架构：将集群的部分实例迁移到新机器，迁移保持规格、版本不变；主从架构：主从实例成对迁移到新机器上，可选择部分实例迁移，也可整机所有实例一起迁移。',
        )
      " />
    <DbForm
      class="toolbox-form mt-16 mb-24"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('升级类型')"
        property="updateType"
        required>
        <CardCheckbox
          v-model="formData.architectureType"
          :desc="t('如 TendisCache 等，迁移过程保持规格、版本不变')"
          icon="cluster"
          :title="t('集群架构')"
          true-value="cluster" />
        <CardCheckbox
          v-model="formData.architectureType"
          class="ml-8"
          :desc="t('支持部分或整机所有实例成对迁移至新主机，版本规格可变')"
          :disabled-tooltips="t('单节点仅支持原地升级')"
          icon="gaokeyong"
          :title="t('主从架构')"
          true-value="masterSlave" />
      </BkFormItem>
      <BkFormItem
        :label="t('迁移类型')"
        property="updateType"
        required>
        <CardCheckbox
          v-model="formData.migrateType"
          :desc="t('只迁移目标实例')"
          icon="fill-1"
          :title="t('实例迁移')"
          true-value="instance" />
        <CardCheckbox
          v-model="formData.migrateType"
          class="ml-8"
          :desc="t('主机关联的所有实例一并迁移')"
          :disabled="formData.architectureType === 'cluster'"
          icon="host"
          :title="t('整机迁移')"
          true-value="machine" />
      </BkFormItem>
    </DbForm>
    <Component
      :is="currentTable"
      :remark="remark"
      :table-list="tableList" />
  </div>
</template>

<script setup lang="tsx">
  import { BkFormItem } from 'bkui-vue/lib/form';
  import { useI18n } from 'vue-i18n';

  import { useTicketCloneInfo } from '@hooks';

  import { TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import RenderClusterInstance from './components/cluseter-instance/Index.vue';
  import type { IDataRow as ClusterInstanceRow } from './components/cluseter-instance/Row.vue';
  import RenderMasterInstance from './components/master-slave-instance/Index.vue';
  import type { IDataRow as MasterSlaveInstanceRow } from './components/master-slave-instance/Row.vue';
  import RenderMasterSlaveHost from './components/master-slave-machine/Index.vue';
  import type { IDataRow as MasterSlaveMachineRow } from './components/master-slave-machine/Row.vue';

  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
    onSuccess(cloneData) {
      tableList.value = cloneData.tableDataList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_SINGLE_INS_MIGRATE,
    onSuccess(cloneData) {
      formData.architectureType = 'masterSlave';

      nextTick(() => {
        if (!cloneData.isDomain) {
          formData.migrateType = 'machine';
        }
      });
      setTimeout(() => {
        tableList.value = cloneData.tableDataList;
        remark.value = cloneData.remark;
        window.changeConfirm = true;
      });
    },
  });

  const initFormData = () => ({
    architectureType: 'cluster', // cluster | masterSlave
    migrateType: 'instance', // instance | machine
  });

  const remark = ref('');

  const tableList = shallowRef<ClusterInstanceRow[] | MasterSlaveInstanceRow[] | MasterSlaveMachineRow[]>([]);

  const formData = reactive(initFormData());

  const renderKey = computed(() => `${formData.architectureType}-${formData.migrateType}`);

  const currentTable = computed(() => {
    const [architectureType, migrateType] = renderKey.value.split('-');
    if (architectureType === 'cluster') {
      return RenderClusterInstance;
    }

    if (migrateType === 'instance') {
      return RenderMasterInstance;
    }

    return RenderMasterSlaveHost;
  });

  watch(
    () => formData.architectureType,
    () => {
      formData.migrateType = 'instance';
    },
  );

  watch(renderKey, () => {
    tableList.value = [];
    remark.value = '';
  });
</script>

<style lang="less" scoped>
  .redis-migrate {
    padding-bottom: 20px;

    .card-checkbox {
      width: 400px;
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
