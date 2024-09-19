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
    <DbOriginalTable
      :columns="columns"
      :data="modelValue"
      :empty-text="t('请选择访问DB')"
      :height="300" />
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
      trigger: 'change',
      message: t('请添加权限规则'),
      validator: (value: PermissionRule['rules']) => value.length > 0,
    },
  ];

  const columns = [
    {
      label: 'DB',
      field: 'access_db',
      showOverflowTooltip: true,
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => {
        if (!cell) {
          return '--';
        }
        return cell.replace(/,/g, ', ');
      },
    },
  ];
</script>
