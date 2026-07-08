<template>
  <div class="staff-manage-member-display">
    <template v-if="type === 'tag'">
      <TagBlock
        :copy-data="value"
        :data="value.map((item) => getDisplayText(item))" />
    </template>
    <template v-else>
      <span :class="{ 'default-user': isDefault }">{{ getDisplayText(value[0]) }}</span>
      <span
        v-if="isDefault"
        class="default-text">
        （{{ t('兜底') }}）
      </span>
    </template>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getUserList } from '@services/source/user';

  import TagBlock from '@components/tag-block/Index.vue';

  interface Props {
    isDefault?: boolean; // 是否兜底
    type?: 'text' | 'tag';
    value: string[];
  }

  const props = withDefaults(defineProps<Props>(), {
    isDefault: false,
    type: 'text',
  });

  const { t } = useI18n();

  const userDataMap = computed(() =>
    Object.fromEntries((userData.value?.results || []).map((item) => [item.username, item.display_name])),
  );

  const { data: userData, loading: isGetUserListLoading, run: runGetUserList } = useRequest(getUserList);

  watch(
    () => props.value,
    (newVal, oldValue) => {
      if (_.isEqual(newVal, oldValue)) {
        return;
      }

      if (props.value.length > 0) {
        runGetUserList({
          exact_lookups: props.value.join(','),
        });
      }
    },
    {
      immediate: true,
    },
  );

  const getDisplayText = (user: string) => {
    if (isGetUserListLoading.value || !userDataMap.value[user]) {
      return user;
    }
    return `${user}（${userDataMap.value[user]}）`;
  };
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
