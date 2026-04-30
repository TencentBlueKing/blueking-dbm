<template>
  <div
    v-bk-loading="loadingConfig"
    class="db-app-select-search-empty">
    <div class="empty-title">{{ t('未找到业务，请确认输入正确') }}</div>
    <div class="empty-subtitle mt-4">
      {{
        defaultAdmin ? t('若业务未纳管，请联系n完成纳管', { n: defaultAdmin }) : t('若业务未纳管，请联系管理员完成纳管')
      }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins } from '@services/source/dbadmin';

  import { DBTypes } from '@common/const';

  interface Props {
    theme?: 'light' | 'dark';
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();

  const isApplyPage = ((route.name || '') as string).includes('_APPLY');
  const dbType = route.meta.dbType as DBTypes;

  const defaultAdmin = computed(() =>
    admins.value && admins.value.data.length > 0
      ? admins.value.data.find((item) => item.db_type === dbType)?.users[0]
      : '',
  );
  const loadingConfig = computed(() => {
    return {
      color: props.theme === 'dark' ? '#182233' : undefined,
      loading: loading.value,
    };
  });

  const {
    data: admins,
    loading,
    run: runGetAdmins,
  } = useRequest(getAdmins, {
    manual: true,
  });

  if (isApplyPage && dbType) {
    runGetAdmins({
      bk_biz_id: 0,
    });
  }
</script>

<style lang="less">
  .db-app-select-search-empty {
    text-align: center;

    .empty-subtitle {
      color: #979ba5;
    }
  }
</style>
