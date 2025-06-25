<template>
  <div class="cluster-tag-list-box">
    <span v-if="!totalList.length">--</span>
    <template v-else>
      <div
        v-if="isVertical"
        class="list-display-main">
        <TextOverflowLayout
          v-for="(item, index) in renderList"
          :key="index">
          {{ item.key }} : {{ item.value.join(' , ') }}
          <template
            v-if="index === 0"
            #append>
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
          </template>
        </TextOverflowLayout>
        <template v-if="isShowMore">
          <BkButton
            v-bk-tooltips="tooltip"
            text
            theme="primary">
            {{ t('共n个', [totalList.length]) }}
          </BkButton>
        </template>
      </div>
      <div
        v-else
        class="list-display-main">
        <RenderTagOverflow :data="horizontalTagList" />
      </div>
    </template>
    <AuthButton
      v-if="!isVertical || (isVertical && !totalList.length)"
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
    :data="data.availableTags"
    :domain="data.masterDomain"
    @success="handleOperateSuccess" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ClusterCommonInfo } from '@services/types';

  import RenderTagOverflow from '@components/render-tag-overflow/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAddTag from './components/AddTag.vue';

  interface Props {
    data: { permission: Record<string, boolean> } & ClusterCommonInfo;
    mode?: 'horizontal' | 'vertical';
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    mode: 'horizontal',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const renderInstanceCount = 6;

  const isShowAddTag = ref(false);

  const isVertical = computed(() => props.mode === 'vertical');

  const totalList = computed(() =>
    props.data.availableTags.map((item) => ({
      key: item.key,
      value: [item.value],
    })),
  );
  const renderList = computed(() => totalList.value.slice(0, renderInstanceCount));
  const isShowMore = computed(() => totalList.value.length > renderInstanceCount);
  const tooltip = computed(() => totalList.value.map((item) => `${item.key}: ${item.value.join(',')}`).join('\n'));
  const actionId = computed(() => `${props.data.db_type}_edit`);
  const horizontalTagList = computed(() => renderList.value.map((item) => `${item.key} : ${item.value.join(' , ')}`));

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
    display: inline-flex;
    align-items: center;

    &:hover {
      .edit-main {
        display: block;
      }
    }

    .empty-main {
      display: flex;
      align-items: center;
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
