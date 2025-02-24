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
      message: t('请添加权限规则'),
      trigger: 'change',
      validator: (value: PermissionRule['rules']) => value.length > 0,
    },
  ];

  const columns = [
    {
      field: 'access_db',
      label: 'DB',
      showOverflowTooltip: true,
    },
    {
      field: 'privilege',
      label: t('权限'),
      render: ({ cell }: { cell: string }) => {
        if (!cell) {
          return '--';
        }
        return cell.replace(/,/g, ', ');
      },
      showOverflowTooltip: true,
    },
  ];
</script>
