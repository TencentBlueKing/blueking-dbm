<template>
  <BkPopConfirm
    :confirm-config="{
      theme: 'danger',
      loading: deleteDbVersionLoading,
    }"
    :confirm-text="t('删除')"
    :content="t('删除操作无法撤回，请谨慎操作！')"
    placement="bottom"
    :popover-options="{
      disabled: isAppliedInstance,
    }"
    :title="t('确认删除该版本？')"
    trigger="click"
    width="280"
    @confirm="handleDeleteVersion">
    <BkButton
      v-bk-tooltips="{
        content: t('含有实例，无法删除'),
        disabled: !isAppliedInstance,
      }"
      class="ml-12"
      :disabled="isAppliedInstance"
      :loading="deleteDbVersionLoading"
      size="small"
      text
      theme="primary">
      {{ t('删除') }}
    </BkButton>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { deleteDbVersion } from '@services/source/version';

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

  const isAppliedInstance = computed(() => {
    const packages = props.data?.packages;
    return Array.isArray(packages) && packages.length > 0 && packages.some((item) => item.instances > 0);
  });

  const { loading: deleteDbVersionLoading, run: runDeleteDbVersion } = useRequest(deleteDbVersion, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('删除成功'));
      emits('success');
    },
  });

  const handleDeleteVersion = () => {
    runDeleteDbVersion({
      id: props.data!.id,
    });
  };
</script>
