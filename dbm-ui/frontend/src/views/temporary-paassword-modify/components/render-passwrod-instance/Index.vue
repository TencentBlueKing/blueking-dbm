<template>
  <Teleport to="#dbContentHeaderAppend">
    <div
      ref="subTitleRef"
      class="password-temporary-modify-head">
      <span class="head-subtitle"> ( {{ t('修改的是管理账号的密码') }} ) </span>
      <AuthButton
        action-id="admin_pwd_view"
        resource="mysql"
        text
        theme="primary"
        @click="passwordSidesliderShow = true">
        <div class="head-button">
          <DbIcon type="history-2 mr-4" />
          <span class="head-button-text">{{ t('临时密码生效的实例') }}</span>
        </div>
      </AuthButton>
    </div>
  </Teleport>
  <RenderInstance v-model="passwordSidesliderShow" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderInstance from './RenderInstance.vue';

  const { t } = useI18n();

  const passwordSidesliderShow = ref(false);
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
