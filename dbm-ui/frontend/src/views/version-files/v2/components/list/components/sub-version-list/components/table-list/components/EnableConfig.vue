<template>
  <BkPopConfirm
    ref="popConfirmRef"
    :title="confirmTitle"
    trigger="click"
    :width="350"
    @after-hidden="handleCancel"
    @confirm="handleConfirm">
    <template #content>
      <div class="mb-16">
        <template v-if="props.data?.enable">
          <div>{{ t('停用后，新部署、升级等场景将无法选择该版本，故障替换按原版本替换不受影响。') }}</div>
          <div>{{ t('注意：停用也将自动清除该版本的 “推荐” 标记') }}</div>
        </template>
        <span v-else>
          {{ t('确认后，该版本将加入可选版本列表，所有场景均可选择使用，如：部署、升级。') }}
        </span>
      </div>
    </template>
    <BkSwitcher
      :before-change="handleBeforeChange"
      :model-value="localValue"
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
    data?: DbVersionModel;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(false);

  const confirmTitle = computed(() =>
    props.data?.enable
      ? t('确认停用该版本（version）？', { version: props.data?.full_version || '' })
      : t('确认启用该版本（version）？', { version: props.data?.full_version || '' }),
  );

  let handleSetEnableResolver: (value: boolean) => void;
  let handleSetEnableRejecter: (value: boolean) => void;

  watch(
    () => props.data,
    () => {
      if (props.data) {
        localValue.value = props.data.enable;
      }
    },
    {
      immediate: true,
    },
  );

  const handleBeforeChange = () => {
    return new Promise<boolean>((resolve, reject) => {
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
    messageSuccess(t('更新成功'));
    emits('success');
    return true;
  };

  const handleCancel = () => {
    handleSetEnableRejecter(false);
  };
</script>
