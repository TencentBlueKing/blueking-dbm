<template>
  <div class="cluster-tag-list-box">
    <div class="list-display-main">
      <TextOverflowLayout
        v-for="(item, index) in renderList"
        :key="index">
        {{ item.key }} : {{ item.value.join(' , ') }}
      </TextOverflowLayout>
      <template v-if="!totalList.length"> -- </template>
      <template v-if="isShowMore">
        <BkButton
          v-bk-tooltips="tooltip"
          text
          theme="primary">
          {{ t('共n个', [totalList.length]) }}
        </BkButton>
      </template>
    </div>
    <AuthButton
      :action-id="actionId"
      class="edit-main"
      :permission="checkEditPermission(data)"
      :resource="data.id"
      text
      theme="primary"
      @click="handleOpenAddTag">
      <DbIcon type="edit" />
    </AuthButton>
  </div>
  <ClusterAddTag
    v-model:is-show="isShowAddTag"
    :cluster-id="data.id"
    :data="data.sortedTags"
    :domain="data.masterDomain"
    @success="handleOperateSuccess" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ClusterCommonInfo } from '@services/types';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAddTag from './components/AddTag.vue';

  interface Props {
    data: { permission: Record<string, boolean> } & ClusterCommonInfo;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const renderInstanceCount = 6;

  const isShowAddTag = ref(false);

  const totalList = computed(() =>
    props.data.sortedTags.map((item) => ({
      key: item.key,
      value: [item.value],
    })),
  );
  const renderList = computed(() => totalList.value.slice(0, renderInstanceCount));
  const isShowMore = computed(() => totalList.value.length > renderInstanceCount);
  const tooltip = computed(() => totalList.value.map((item) => `${item.key}: ${item.value.join(',')}`).join('\n'));
  const actionId = computed(() => `${props.data.db_type}_edit`);

  const checkEditPermission = (data: Props['data']) => {
    const permissionKey = `${props.data.db_type}_edit`;
    return data.permission[permissionKey];
  };

  const handleOperateSuccess = () => {
    emits('success');
  };

  const handleOpenAddTag = () => {
    isShowAddTag.value = true;
  };
</script>

<style lang="less">
  .cluster-tag-list-box {
    display: flex;
    align-items: center;

    &:hover {
      .edit-main {
        display: block;
      }
    }

    .list-display-main {
      flex: 1;
      overflow: hidden;
    }

    .edit-main {
      display: none;
      margin-left: 8px;
    }
  }
</style>
