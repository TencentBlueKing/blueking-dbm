<template>
  <BkFormItem
    v-model="modelValue"
    :label="t('权限明细')"
    property="rules"
    :rules="rules">
    <BkAlert
      class="mb-16 mt-10"
      theme="warning"
      :title="t('注意_对从域名授权时仅会授予 select 权限')" />
    <PrimaryTable
      :data="modelValue"
      :height="300"
      row-key="access_db">
      <TableColumn
        col-key="access_db"
        ellipsis
        title="DB" />
      <TableColumn
        col-key="privilege"
        ellipsis
        :title="t('权限')">
        <template #default="{ row }">
          {{ row.privilege ? row.privilege.replace(/,/g, ', ') : '--' }}
        </template>
      </TableColumn>
    </PrimaryTable>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { PermissionRule } from '@services/types';

  const modelValue = defineModel<PermissionRule['rules']>('modelValue', {
    default: () => [],
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('请添加权限规则'),
      trigger: 'change',
      validator: (value: PermissionRule['rules']) => value.length > 0,
    },
  ];
</script>
