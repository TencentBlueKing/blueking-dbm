<template>
  <BkFormItem
    :label="t('访问DB')"
    property="access_dbs"
    required
    :rules="rules">
    <BkSelect
      v-model="accessDbs"
      :clearable="false"
      collapse-tags
      filterable
      :input-search="false"
      multiple
      multiple-mode="tag"
      show-select-all>
      <BkOption
        v-for="item of accountRules"
        :key="item.rule_id"
        :label="item.access_db"
        :value="item.access_db" />
      <template #extension>
        <BkButton
          class="to-create-rules"
          text
          @click="handleToCreateRules">
          <DbIcon
            class="mr-4"
            type="plus-circle" />
          {{ t('跳转新建规则') }}
        </BkButton>
      </template>
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { PermissionRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  interface Props {
    accountType: AccountTypes;
    accountRules: PermissionRule['rules'];
  }

  const props = defineProps<Props>();

  const accessDbs = defineModel<string[]>('modelValue', {
    default: () => [],
  });

  const router = useRouter();
  const { t } = useI18n();

  const rules = [
    {
      trigger: 'blur',
      message: t('请选择访问DB'),
      validator: (value: string[]) => value.length > 0,
    },
  ];

  /**
   * 跳转新建规则界面
   */
  const handleToCreateRules = () => {
    const routeMap = {
      [AccountTypes.MYSQL]: 'PermissionRules',
      [AccountTypes.TENDBCLUSTER]: 'spiderPermission',
      [AccountTypes.MONGODB]: 'MongodbPermission',
      [AccountTypes.SQLSERVER]: 'SqlServerPermissionRules',
    };
    const url = router.resolve({ name: routeMap[props.accountType] });
    window.open(url.href, '_blank');
  };
</script>
