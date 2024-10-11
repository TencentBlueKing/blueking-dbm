<template>
  <h5 class="cluster-authorize-bold cluster-authorize-label pb-16">
    {{ t('权限规则') }}
  </h5>
  <UserSelect
    v-bind="props"
    v-model="user"
    @success="handleSuccess" />
  <DbSelect
    v-bind="props"
    v-model:access-dbs="accessDbs"
    v-model:rules="rules"
    v-model:user="user"
    :account-rules="accountRules" />
  <RulesTable v-model="rules" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { PermissionRule } from '@services/types';

  import { AccountTypes } from '@common/const';

  import DbSelect from './components/DbSelect.vue';
  import RulesTable from './components/RulesTable.vue';
  import UserSelect from './components/UserSelect.vue';

  interface Props {
    accountType: AccountTypes;
  }

  const props = defineProps<Props>();

  const user = defineModel<string>('user', {
    default: '',
  });

  const accessDbs = defineModel<string[]>('accessDbs', {
    default: () => [],
  });

  const rules = defineModel<PermissionRule['rules']>('rules', {
    default: () => [],
  });

  const { t } = useI18n();

  const accountRules = ref<PermissionRule[]>([]);

  const handleSuccess = (data: PermissionRule[]) => {
    accountRules.value = data;
  };
</script>

<style lang="less" scoped>
  .to-create-rules {
    display: inline-block;
    margin-left: 16px;
    line-height: 40px;

    i {
      color: @gray-color;
    }

    &:hover {
      color: @primary-color;

      i {
        color: @primary-color;
      }
    }
  }
</style>
