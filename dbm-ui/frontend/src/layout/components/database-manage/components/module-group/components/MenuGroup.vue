<template>
  <BkMenuGroup class="module-menu-group">
    <template #name>
      {{ dbInfo.name }}
      <DbIcon
        v-if="!isError"
        v-bk-tooltips="disabled ? t('当前数据库已置顶') : t('置顶当前数据库')"
        class="top-button"
        :class="{ 'top-button-disabled': disabled }"
        type="zhiding"
        @click="handleClick" />
    </template>
    <slot />
  </BkMenuGroup>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import { DBTypeInfos, DBTypes, UserPersonalSettings } from '@common/const';

  interface Props {
    dbType: DBTypes;
    isError: boolean;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const userProfileStore = useUserProfile();

  const dbInfo = DBTypeInfos[props.dbType];

  const topDbTypes = computed<string[]>(() => userProfileStore.profile[UserPersonalSettings.TOP_DB_TYPES] || []);
  const disabled = computed(() => topDbTypes.value.includes(props.dbType));

  const handleClick = () => {
    if (disabled.value) {
      return;
    }
    userProfileStore.updateProfile({
      label: UserPersonalSettings.TOP_DB_TYPES,
      values: [props.dbType],
    });
  };
</script>

<style lang="less">
  .module-menu-group {
    .group-name {
      padding: 0 18px;
      margin: 0 !important;

      &:hover {
        background-color: #2b313f;

        .top-button {
          display: inline-block;
        }
      }
    }

    .top-button {
      display: none;
      margin-left: auto;
      font-size: 18px;
      color: #c4c6cc;

      &:hover {
        display: inline-block;
        color: #fff;
      }
    }

    .top-button-disabled {
      color: #dcdee5;
      cursor: not-allowed;

      &:hover {
        color: #dcdee5;
      }
    }
  }
</style>
