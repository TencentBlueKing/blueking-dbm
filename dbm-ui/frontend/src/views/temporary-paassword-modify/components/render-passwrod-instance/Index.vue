<template>
  <Teleport to="#dbContentHeaderAppend">
    <div
      ref="subTitleRef"
      class="password-temporary-modify-head">
      <span class="head-subtitle"> ( {{ t('修改的是管理账号的密码') }} ) </span>
      <BkButton
        text
        theme="primary"
        @click="passwordSidesliderShow = true">
        <div class="head-button">
          <DbIcon type="history-2 mr-4" />
          <span class="head-button-text">{{ t('查看临时密码') }}</span>
        </div>
      </BkButton>
    </div>
  </Teleport>
  <RenderInstance
    v-model="passwordSidesliderShow"
    v-model:db-type="dbType" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import { DBTypes } from '@common/const';

  import RenderInstance from './RenderInstance.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const passwordSidesliderShow = ref(false);
  const dbType = ref<DBTypes>(DBTypes.MYSQL);

  // URL 携带 db_type 时自动打开侧滑并定位 Tab，方便分享链接
  const urlDbType = route.query.db_type as DBTypes;
  if (urlDbType && Object.values(DBTypes).includes(urlDbType)) {
    dbType.value = urlDbType;
    passwordSidesliderShow.value = true;
  }

  // 切换 Tab 时同步 URL
  watch(dbType, (val) => {
    router.replace({ query: { ...route.query, db_type: val } });
  });
</script>
<style lang="less" scoped>
  .password-temporary-modify-head {
    display: flex;
    margin-left: 8px;
    flex: 1;
    line-height: 1.7;
    justify-content: space-between;

    .head-subtitle {
      font-size: 12px;
      color: #979ba5;
    }

    .head-button {
      display: flex;
      align-items: center;

      .head-button-text {
        font-size: 12px;
      }
    }
  }
</style>
