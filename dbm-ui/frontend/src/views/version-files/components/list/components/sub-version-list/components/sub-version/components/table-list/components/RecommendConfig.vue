<template>
  <BkButton
    v-bk-tooltips="{
      content: t('未启用的版本无法设置'),
      disabled: data.enable,
    }"
    class="set-recommended"
    :disabled="!data.enable"
    :loading="updateDbVersionLoading"
    size="small"
    @click="handleSetRecommended">
    {{ t('设为推荐版本') }}
  </BkButton>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

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

  const { loading: updateDbVersionLoading, run: runUpdateDbVersion } = useRequest(updateDbVersion, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('更新成功'));
      emits('success');
    },
  });

  const handleSetRecommended = () => {
    runUpdateDbVersion({
      id: props.data!.id,
      phase: props.data!.phase,
      recommend: true,
    });
  };
</script>
