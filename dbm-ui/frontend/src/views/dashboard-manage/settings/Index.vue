<template>
  <PrimaryTable :data="dashboardList">
    <TableColumn
      col-key="uid"
      :title="t('名称')">
      <template #default="{ row }">
        <RouterLink
          target="_blank"
          :to="{
            name: 'DashboradView',
            params: {
              versionId: row.uid,
            },
          }">
          {{ row.name }}
        </RouterLink>
      </template>
    </TableColumn>
    <TableColumn
      col-key="uid"
      :title="t('操作')"
      :width="120">
      <BkSwitcher size="small" />
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAppShareList } from '@services/source/bkVersion';

  const { t } = useI18n();
  const { data: dashboardList } = useRequest(getAppShareList);
</script>
