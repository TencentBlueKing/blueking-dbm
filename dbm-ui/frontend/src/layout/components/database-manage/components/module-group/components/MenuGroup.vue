<template>
  <BkMenuGroup :name="dbInfo.name">
    <slot />
    <DbIcon
      v-if="!topDbTypes.includes(dbType)"
      v-bk-tooltips="t('将该导航菜单置顶')"
      class="top-button"
      type="zhiding"
      @click="handleClick" />
  </BkMenuGroup>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import { DBTypeInfos, DBTypes, UserPersonalSettings } from '@common/const';

  interface Props {
    dbType: DBTypes;
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
