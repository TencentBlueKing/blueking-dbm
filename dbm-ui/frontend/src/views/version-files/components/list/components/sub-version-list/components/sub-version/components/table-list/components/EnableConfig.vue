<template>
  <BkSwitcher
    v-model="localValue"
    :before-change="handleSetEnable"
    size="small"
    theme="primary" />
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

  const handleSetEnable = async (value: boolean) => {
    await updateDbVersion({
      enable: value,
      id: props.data!.id,
      phase: props.data!.phase,
    });
    messageSuccess(t('更新成功'));
    emits('success');
    return true;
  };
</script>
