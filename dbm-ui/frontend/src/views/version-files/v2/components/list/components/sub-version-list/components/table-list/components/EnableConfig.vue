<template>
  <BkPopConfirm
    ref="popConfirmRef"
    ext-cls="version-files-enable-config-main"
    :title="confirmTitle"
    trigger="click"
    :width="350"
    @after-hidden="handleCancel"
    @confirm="handleConfirm">
    <template #content>
      <div class="mb-16">
        <template v-if="data.enable">
          <div>{{ t('停用后，新部署、升级等场景将无法选择该版本，故障替换按原版本替换不受影响。') }}</div>
          <div v-if="data.recommend">{{ t('注意：停用也将自动清除该版本的 “推荐” 标记') }}</div>
        </template>
        <span v-else>
          {{ t('确认后，该版本将加入可选版本列表，所有场景均可选择使用，如：部署、升级。') }}
        </span>
      </div>
    </template>
    <AuthSwitcher
      action-id="package_manage"
      :before-change="handleBeforeChange"
      :disabled="!permission"
      :model-value="localValue"
      :permission="permission"
      :resource="dbType"
      size="small"
      theme="primary" />
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { updateDbVersion } from '@services/source/version';

  import { messageSuccess } from '@utils';

  interface Props {
    data: DbVersionModel;
    dbType: string;
    permission: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(false);

  const confirmTitle = computed(() =>
    props.data?.enable
      ? t('确认停用该版本（version）？', { version: props.data.name || '' })
      : t('确认启用该版本（version）？', { version: props.data.name || '' }),
  );

  let handleSetEnableResolver: (value: boolean) => void;
  let handleSetEnableRejecter: (value: boolean) => void;

  watch(
    () => props.data,
    () => {
      localValue.value = props.data.enable;
    },
    {
      immediate: true,
    },
  );

  const handleBeforeChange = () => {
    return new Promise<boolean>((resolve, reject) => {
      if (!props.permission) {
        reject(false);
        return;
      }
      handleSetEnableResolver = resolve;
      handleSetEnableRejecter = reject;
    });
  };

  const handleConfirm = async () => {
    localValue.value = !localValue.value;
    await updateDbVersion({
      enable: localValue.value,
      id: props.data!.id,
      phase: props.data!.phase,
    });
    handleSetEnableResolver(true);
    messageSuccess(t('操作成功'));
    emits('success');
    return true;
  };

  const handleCancel = () => {
    handleSetEnableRejecter(false);
  };
</script>
<style lang="less">
  .version-files-enable-config-main {
    .bk-pop-confirm-title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
