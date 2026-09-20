<template>
  <div class="staff-manage-member-display">
    <UserNameList
      v-if="type === 'tag'"
      :data="value" />
    <template v-else>
      <bk-user-display-name
        :class="{ 'default-user': isDefault }"
        :user-id="value[0] ?? ''" />
      <span
        v-if="isDefault"
        class="default-text">
        （{{ t('兜底') }}）
      </span>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import UserNameList from '@components/user-name-list/Index.vue';

  interface Props {
    isDefault?: boolean; // 是否兜底
    type?: 'text' | 'tag';
    value: string[];
  }

  withDefaults(defineProps<Props>(), {
    isDefault: false,
    type: 'text',
  });

  const { t } = useI18n();
</script>

<style lang="less">
  .staff-manage-member-display {
    .default-user {
      color: #c4c6cc;
    }

    .default-text {
      color: #f8b64f;
    }
  }
</style>
