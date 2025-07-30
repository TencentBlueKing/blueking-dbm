<template>
  <BkMenuGroup class="module-menu-group">
    <template #name>
      {{ dbInfo.name }}
      <DbIcon
        v-if="!topDbTypes.includes(dbType) && !isError"
        v-bk-tooltips="t('将该导航菜单置顶')"
        class="top-button"
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

  const handleClick = () => {
    userProfileStore.updateProfile({
      label: UserPersonalSettings.TOP_DB_TYPES,
      values: [props.dbType, ...topDbTypes.value],
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
    }
  }
</style>
