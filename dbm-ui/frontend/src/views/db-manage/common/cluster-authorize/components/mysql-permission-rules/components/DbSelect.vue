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
        <div
          class="default-display-main"
          @click="handleToCreateRules">
          <DbIcon
            class="add-account-icon"
            type="plus-circle" />
          <span>{{ t('跳转新建规则') }}</span>
        </div>
      </template>
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { PermissionRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  interface Props {
    accountRules: PermissionRule['rules'];
    accountType: AccountTypes;
  }

  const props = defineProps<Props>();

  const accessDbs = defineModel<string[]>('modelValue', {
    default: () => [],
  });

  const router = useRouter();
  const { t } = useI18n();

  const rules = [
    {
      message: t('请选择访问DB'),
      trigger: 'blur',
      validator: (value: string[]) => value.length > 0,
    },
  ];

  /**
   * 跳转新建规则界面
   */
  const handleToCreateRules = () => {
    const routeMap = {
      [AccountTypes.MONGODB]: 'MongodbPermission',
      [AccountTypes.MYSQL]: 'PermissionRules',
      [AccountTypes.SQLSERVER]: 'SqlServerPermissionRules',
      [AccountTypes.TENDBCLUSTER]: 'spiderPermission',
    };
    const url = router.resolve({ name: routeMap[props.accountType] });
    window.open(url.href, '_blank');
  };
</script>
<style lang="less">
  .default-display-main {
    font-family: MicrosoftYaHei, Arial, sans-serif;
    color: #4d4f56;
    cursor: pointer;

    .add-account-icon {
      margin-right: 5px;
      font-size: 14px;
      color: #979ba5;
    }
  }
</style>
