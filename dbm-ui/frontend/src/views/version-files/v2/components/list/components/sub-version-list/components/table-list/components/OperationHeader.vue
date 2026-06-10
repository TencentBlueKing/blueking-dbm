<template>
  <div
    v-if="!isEditName"
    class="title-operate">
    <div class="title-main">
      <span>{{ versionName }}</span>
      <BkTag
        class="ml-12"
        radius="12px">
        {{ dbVersionListCount }}
      </BkTag>
    </div>
    <div class="more-operate">
      <div
        class="icon-wrapper"
        @click.stop="handleShowOperatePanel">
        <DbIcon type="more" />
      </div>
      <div
        v-show="isShowOperatePanel"
        v-clickoutside="handleClickOutside"
        class="operate-panel-list"
        :style="{
          top: `${operatePanelPosition.top}px`,
          left: `${operatePanelPosition.left}px`,
        }">
        <AuthTemplate
          action-id="package_manage"
          class="operate-item add-veriosn"
          :class="{ 'is-disabled': !permission }"
          :permission="permission"
          :resource="dbType"
          @click.stop="handleAddVersion">
          {{ t('添加版本') }}
        </AuthTemplate>
        <AuthTemplate
          action-id="package_manage"
          class="operate-item"
          :class="{ 'is-disabled': !permission }"
          :permission="permission"
          :resource="dbType"
          @click.stop="handleEditName">
          {{ t('编辑系列') }}
        </AuthTemplate>
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
          <AuthTemplate
            v-bk-tooltips="{
              content: t('该版本系列下存在 n 个版本，请删除后再操作', { n: dbVersionListCount }),
              placement: 'right',
              disabled: dbVersionListCount === 0,
            }"
            action-id="package_manage"
            class="operate-item"
            :class="{ 'is-disabled': dbVersionListCount > 0 || !permission }"
            :permission="permission"
            :resource="dbType"
            @click.stop>
            {{ t('删除系列') }}
          </AuthTemplate>
        </BkPopConfirm>
      </div>
    </div>
  </div>
  <EditSeries
    v-else
    v-model:is-edit="isEditName"
    class="operation-header-edit-series-main"
    :data="versionName"
    :distribution-id="data?.distribution"
    :existed-list="existedVersionNameList"
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
    dbType: string;
    dbVersionListCount?: number;
    existedVersionNameList: string[];
    permission?: boolean;
  }

  interface Emits {
    (e: 'addNewVersion'): void;
    (e: 'editVersionSeries'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    dbVersionListCount: 0,
    permission: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isEditName = ref(false);
  const isShowOperatePanel = ref(false);
  const versionName = ref('');
  const operatePanelPosition = ref({
    left: 0,
    top: 0,
  });

  const { loading: deleteVersionSeriesLoading, run: runDeleteVersionSeries } = useRequest(deleteVersionSeries, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('editVersionSeries');
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
    emits('editVersionSeries');
  };

  const handleEditName = () => {
    isShowOperatePanel.value = false;
    isEditName.value = true;
  };

  const handleShowOperatePanel = (e: MouseEvent) => {
    const target = e.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    operatePanelPosition.value = {
      left: rect.left + rect.width,
      top: rect.bottom,
    };
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

    .more-operate {
      position: relative;
      display: flex;
      width: 26px;
      height: 26px;
      margin-left: 4px;

      .icon-wrapper {
        display: flex;
        width: 26px;
        height: 26px;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        &:hover {
          background: #dcdee5;
        }
      }

      .operate-panel-list {
        position: fixed;
        // top: 30px;
        // left: 10px;
        z-index: 999999;
        width: 120px;
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

          &.add-veriosn {
            height: 32px;
            border-bottom: solid 1px #f0f1f5;
          }
        }
      }
    }
  }

  .operation-header-edit-series-main {
    .edit-main {
      padding: 0;

      .edit-input-main {
        max-width: 500px;
      }
    }
  }
</style>
