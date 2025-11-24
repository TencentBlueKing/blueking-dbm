<template>
  <div
    v-if="!isEditName"
    class="title-operate">
    <div class="title-main">{{ versionName }}</div>
    <div class="operate-main">
      <BkButton
        class="ml-8"
        size="small"
        @click.stop="handleAddVersion">
        {{ t('添加版本') }}
      </BkButton>
      <div class="more-operate">
        <DbIcon
          type="more"
          @click.stop="handleShowOperatePanel" />
        <div
          v-show="isShowOperatePanel"
          v-clickoutside="handleClickOutside"
          class="operate-panel-list">
          <div
            class="operate-item"
            @click.stop="handleEditName">
            {{ t('编辑') }}
          </div>
          <BkPopConfirm
            :confirm-config="{
              theme: 'danger',
              loading: deleteVersionSeriesLoading,
            }"
            :confirm-text="t('删除')"
            :content="t('删除操作无法撤回，请谨慎操作！')"
            :disabled="dbVersionListCount > 0"
            placement="bottom"
            :title="t('确认删除该版本系列？')"
            trigger="click"
            width="280"
            @confirm="handleDeleteVersionSeries">
            <div
              v-bk-tooltips="{
                content: t('当前系列包含版本内容，无法删除'),
                placement: 'right',
                disabled: dbVersionListCount === 0,
              }"
              class="operate-item"
              :class="{ 'is-disabled': dbVersionListCount > 0 }"
              @click.stop>
              {{ t('删除') }}
            </div>
          </BkPopConfirm>
        </div>
      </div>
    </div>
  </div>
  <EditSeries
    v-else
    v-model:is-edit="isEditName"
    :data="versionName"
    :distribution-id="data?.distribution"
    mode="update"
    :series-id="data?.id"
    @confirm="handleConfirmChangeVersionName" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteVersionSeries } from '@services/source/version';

  import { messageSuccess } from '@utils';

  import EditSeries from '../../EditSeries.vue';

  interface Props {
    data?: {
      distribution: number;
      id: number;
      name: string;
    };
    dbVersionListCount?: number;
  }

  interface Emits {
    (e: 'addNewVersion'): void;
    (e: 'deleteVersionSeries'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    dbVersionListCount: 0,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isEditName = ref(false);
  const isShowOperatePanel = ref(false);
  const versionName = ref('');

  const { loading: deleteVersionSeriesLoading, run: runDeleteVersionSeries } = useRequest(deleteVersionSeries, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('删除成功'));
      emits('deleteVersionSeries');
    },
  });

  watch(
    () => props.data,
    () => {
      versionName.value = props.data?.name || '';
    },
    {
      immediate: true,
    },
  );

  const handleDeleteVersionSeries = () => {
    runDeleteVersionSeries({
      distribution: props.data!.distribution,
      id: props.data!.id,
    });
  };

  const handleConfirmChangeVersionName = (id: number, name: string) => {
    versionName.value = name;
  };

  const handleEditName = () => {
    isShowOperatePanel.value = false;
    isEditName.value = true;
  };

  const handleShowOperatePanel = () => {
    isShowOperatePanel.value = true;
  };

  const handleAddVersion = () => {
    emits('addNewVersion');
  };

  const handleClickOutside = () => {
    isShowOperatePanel.value = false;
  };
</script>
<style lang="less">
  .title-operate {
    display: flex;
    align-items: center;

    .title-main {
      font-size: 16px;
      font-weight: 700;
      color: #313238;
    }

    .operate-main {
      display: flex;
      align-items: center;

      .more-operate {
        position: relative;
        display: flex;
        width: 26px;
        height: 26px;
        margin-left: 4px;
        cursor: pointer;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        &:hover {
          background: #dcdee5;
        }

        .operate-panel-list {
          position: absolute;
          top: 30px;
          left: 10px;
          z-index: 999;
          width: 60px;
          background: #fff;
          border: 1px solid #dcdee5;
          border-radius: 2px;
          box-shadow: 0 2px 6px 0 #0000001a;

          .operate-item {
            display: flex;
            width: 100%;
            height: 32px;
            padding: 0 12px;
            font-size: 12px;
            color: #4d4f56;
            cursor: pointer;
            align-items: center;

            &:hover {
              background: #f5f7fa;
            }

            &.is-disabled {
              color: #c4c6cc;
              cursor: not-allowed;
            }
          }
        }
      }
    }
  }
</style>
