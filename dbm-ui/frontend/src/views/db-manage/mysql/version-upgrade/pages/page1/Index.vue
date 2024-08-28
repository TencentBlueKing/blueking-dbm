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
  <div class="mysql-version-upgrade-page">
    <BkAlert
      closable
      theme="info"
      :title="
        t(
          '版本升级：接入层可直接原地升级，存储层需先创建相应版本的模块，连续版本可直接升级，跨版本需提供新机通过迁移完成升级；同机所有关联集群将一并升级',
        )
      " />
    <DbForm
      class="upgrade-form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('角色类型')"
        property="roleType"
        required>
        <BkRadioGroup
          v-model="formData.roleType"
          @change="handleRoleTypeChange">
          <BkRadioButton
            v-for="item in roleTypeList"
            :key="item.value"
            :label="item.value"
            style="width: 160px">
            {{ item.label }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        v-if="formData.roleType !== 'haAccessLayer'"
        :label="t('升级类型')"
        property="updateType"
        required>
        <CardCheckbox
          v-model="formData.updateType"
          :desc="t('适用于小版本升级，如 5.6.1 ->  5.6.2 ')"
          icon="rebuild"
          :title="t('原地升级')"
          true-value="local" />
        <CardCheckbox
          v-model="formData.updateType"
          class="ml-8"
          :desc="t('适用于大版本升级，如 5.6.0 ->  5.7.0')"
          :disabled="formData.roleType === 'singleStorageLayer'"
          :disabled-tooltips="t('单节点仅支持原地升级')"
          icon="clone"
          :title="t('迁移升级')"
          true-value="remote" />
      </BkFormItem>
    </DbForm>
    <Component
      :is="currentTable"
      :backup-source="backupSource"
      :remark="remark"
      :table-list="tableList" />
  </div>
</template>

<script setup lang="tsx">
  import { BkFormItem } from 'bkui-vue/lib/form';
  import { useI18n } from 'vue-i18n';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import RenderAccessLayerTable from './components/ha-access-layer/Index.vue';
  import type { IDataRow as HaAccessLayerRow } from './components/ha-access-layer/Row.vue';
  import RenderStorageLayerLocalTable from './components/ha-storage-layer-local/Index.vue';
  import type { IDataRow as HaStorageLayerLocalRow } from './components/ha-storage-layer-local/Row.vue';
  import RenderStorageLayerRemoteTable from './components/ha-storage-layer-remote/Index.vue';
  import type { IDataRow as HaStorageLayerRemoteRow } from './components/ha-storage-layer-remote/Row.vue';
  import RenderSingleStorageTable from './components/single-storage-layer/Index.vue';
  import type { IDataRow as SingleStorageRow } from './components/single-storage-layer/Row.vue';

  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_PROXY_UPGRADE,
    onSuccess(cloneData) {
      tableList.value = cloneData.tableList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
      formData.roleType = 'haAccessLayer';
    },
  });

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_LOCAL_UPGRADE,
    onSuccess(cloneData) {
      tableList.value = cloneData.tableList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;

      const isSingle = cloneData.tableList[0].clusterData.clusterType === ClusterTypes.TENDBSINGLE;
      formData.roleType = isSingle ? 'singleStorageLayer' : 'haStorageLayer';
      formData.updateType = 'local';
    },
  });

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_MIGRATE_UPGRADE,
    onSuccess(cloneData) {
      backupSource.value = cloneData.backupSource;
      remark.value = cloneData.remark;
      window.changeConfirm = true;

      formData.roleType = 'haStorageLayer';
      nextTick(() => {
        formData.updateType = 'remote';
      });
      setTimeout(() => {
        tableList.value = cloneData.tableList;
      });
    },
  });

  const initFormData = () => ({
    roleType: 'haAccessLayer',
    updateType: 'local',
  });

  const roleTypeList = [
    {
      label: t('主从 - 接入层'),
      value: 'haAccessLayer',
    },
    {
      label: t('主从 - 存储层'),
      value: 'haStorageLayer',
    },
    {
      label: t('单节点'),
      value: 'singleStorageLayer',
    },
  ];

  const backupSource = ref('');
  const remark = ref('');

  const tableList = shallowRef<
    HaAccessLayerRow[] | HaStorageLayerLocalRow[] | HaStorageLayerRemoteRow[] | SingleStorageRow[]
  >([]);

  const formData = reactive(initFormData());

  const currentTable = computed(() => {
    const { roleType, updateType } = formData;
    if (roleType === 'haAccessLayer') {
      return RenderAccessLayerTable;
    }
    if (roleType === 'singleStorageLayer') {
      return RenderSingleStorageTable;
    }
    if (updateType === 'local') {
      return RenderStorageLayerLocalTable;
    }
    return RenderStorageLayerRemoteTable;
  });

  watch(
    () => formData.roleType,
    () => {
      formData.updateType = 'local';
    },
  );

  watch(
    () => formData.updateType,
    () => {
      tableList.value = [];
      remark.value = '';
      if (formData.updateType === '') {
        formData.updateType = 'local';
      }
    },
  );

  const handleRoleTypeChange = () => {
    remark.value = '';
    tableList.value = [];
  };
</script>

<style lang="less" scoped>
  .mysql-version-upgrade-page {
    padding-bottom: 20px;

    .upgrade-form {
      margin: 24px 0;

      :deep(.bk-form-label) {
        font-size: 12px;
        font-weight: 700;
        color: #313238;
      }
    }
  }
</style>
