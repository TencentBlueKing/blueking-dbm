<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <ApplyPermissionCatch>
    <div class="backup-storage-config-page">
      <div class="page-toolbar">
        <AuthButton
          action-id="dbconfig_edit"
          resource="common"
          theme="primary"
          @click="handleAdd">
          {{ t('新增配置') }}
        </AuthButton>
        <DbQuickSearch
          v-model="quickSearchValue"
          :data="quickSearchData"
          parse-url
          :placeholder="t('请输入或选择条件搜索')"
          style="width: 500px; margin-left: auto"
          @change="handleQuickSearchChange" />
      </div>
      <BkLoading :loading="loading">
        <PrimaryTable
          :data="filteredData"
          :max-height="tableMaxHeight"
          resizable
          row-key="bk_cloud_id">
          <TableColumn
            col-key="bk_cloud_name"
            :min-width="180"
            :title="t('云区域')">
            <template #default="{ row }: { row: BackupConfigRow }">
              <AuthButton
                action-id="dbconfig_edit"
                :permission="row.permission.dbconfig_edit"
                resource="common"
                text
                theme="primary"
                @click="handleEdit(row)">
                {{ row.bk_cloud_name }}[{{ row.bk_cloud_id }}]
              </AuthButton>
            </template>
          </TableColumn>
          <TableColumn
            col-key="storage_type"
            :min-width="100"
            :title="t('存储类型')">
            <template #default="{ row }: { row: BackupConfigRow }">
              {{ getConfValue(row, 'cos_auth.storage_type') }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="region"
            :min-width="180"
            title="Region">
            <template #default="{ row }: { row: BackupConfigRow }">
              {{ getConfValue(row, 'cos_auth.region') }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="endpoint"
            :min-width="180"
            title="Endpoint">
            <template #default="{ row }: { row: BackupConfigRow }">
              {{ getConfValue(row, 'cos_auth.endpoint') }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="bucket_name"
            :min-width="180"
            title="Bucket">
            <template #default="{ row }: { row: BackupConfigRow }">
              {{ getConfValue(row, 'cos_auth.bucket_name') }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="updated_by"
            :min-width="100"
            :title="t('更新人')">
            <template #default="{ row }: { row: BackupConfigRow }">
              {{ row.updated_by || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="updated_at"
            :min-width="180"
            :title="t('更新时间')" />
          <TableColumn
            col-key="row-operation"
            fixed="right"
            :title="t('操作')"
            :width="100">
            <template #default="{ row }: { row: BackupConfigRow }">
              <AuthButton
                action-id="dbconfig_edit"
                class="mr-8"
                :permission="row.permission.dbconfig_edit"
                resource="common"
                text
                theme="primary"
                @click="handleEdit(row)">
                {{ t('编辑') }}
              </AuthButton>
              <DbPopconfirm
                :confirm-handler="() => handleDelete(row)"
                :content="t('删除后该云区域的所有配置值将被清除')"
                :title="
                  t('确定删除「{n}（{id}）」的备份存储配置？', {
                    id: row.bk_cloud_id,
                    n: row.bk_cloud_name,
                  })
                ">
                <AuthButton
                  action-id="dbconfig_edit"
                  :permission="row.permission.dbconfig_edit"
                  resource="common"
                  text
                  theme="primary">
                  {{ t('删除') }}
                </AuthButton>
              </DbPopconfirm>
            </template>
          </TableColumn>
        </PrimaryTable>
      </BkLoading>

      <!-- 新增/编辑侧滑 -->
      <OperateSideslider
        v-if="showSideslider"
        v-model:show="showSideslider"
        :data="editingRow"
        :existing-cloud-ids="existingCloudIds"
        @saved="handleSaved" />
    </div>
  </ApplyPermissionCatch>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { type BackupConfigRow, deleteBackupConfig, getBackupConfigList } from '@services/source/configs';

  import { useTableMaxHeight } from '@hooks';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import type { Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  import { messageSuccess } from '@utils';

  import OperateSideslider from './components/OperateSideslider.vue';

  const { t } = useI18n();

  const quickSearchValue = ref<Record<string, string>>({});
  const showSideslider = ref(false);
  const editingRow = ref<BackupConfigRow | null>(null);

  const tableMaxHeight = useTableMaxHeight(194);

  const quickSearchData = [
    {
      id: 'bk_cloud_name',
      name: t('云区域'),
      type: 'input',
    },
  ] as QuickSearchProps['data'];

  // 已配置的云区域 ID 列表
  const existingCloudIds = computed(() => tableData.value!.map((item) => Number(item.bk_cloud_id)));

  // 搜索过滤
  const filteredData = computed(() => {
    const { bk_cloud_name: cloudName } = quickSearchValue.value;
    if (!cloudName?.trim()) return tableData.value;
    const keyword = cloudName.trim().toLowerCase();
    return tableData.value!.filter(
      (item) => item.bk_cloud_name.toLowerCase().includes(keyword) || String(item.bk_cloud_id).includes(keyword),
    );
  });

  // 搜索变更
  const handleQuickSearchChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
  };

  // 获取配置值（根据 conf_name 从 conf_items 中取值）
  const getConfValue = (row: BackupConfigRow, confName: string) => {
    const item = row.conf_items.find((i) => i.conf_name === confName);
    return item?.conf_value || '--';
  };

  // 获取列表
  const {
    data: tableData,
    loading,
    run: fetchList,
  } = useRequest(getBackupConfigList, {
    manual: true,
  });

  // 刷新列表
  const refreshList = () => {
    fetchList({ bk_biz_id: window.PROJECT_CONFIG.BIZ_ID }, { permission: 'catch' });
  };

  // 初始加载（传入 permission: 'catch' 由 ApplyPermissionCatch 拦截无权限场景）
  refreshList();

  // 新增
  const handleAdd = () => {
    editingRow.value = null;
    showSideslider.value = true;
  };

  // 编辑
  const handleEdit = (row: BackupConfigRow) => {
    editingRow.value = row;
    showSideslider.value = true;
  };

  // 删除
  const handleDelete = (row: BackupConfigRow) => {
    return deleteBackupConfig({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      conf_file: 'cosinfo.toml',
      conf_type: 'backup_client',
      level_name: 'bk_cloud_id',
      level_value: row.bk_cloud_id,
      meta_cluster_type: 'common',
    }).then(() => {
      messageSuccess(t('删除成功'));
      refreshList();
    });
  };

  // 保存成功回调
  const handleSaved = () => {
    showSideslider.value = false;
    refreshList();
  };
</script>

<style lang="less" scoped>
  .backup-storage-config-page {
    height: calc(100vh - var(--notice-height) - 105px);
    padding: 24px;

    .page-toolbar {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }
  }
</style>
