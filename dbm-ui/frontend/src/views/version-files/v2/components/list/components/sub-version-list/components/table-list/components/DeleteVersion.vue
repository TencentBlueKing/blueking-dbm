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
      disabled: !permission || isAppliedInstance,
    }"
    :title="t('确认删除该版本？')"
    trigger="click"
    width="280"
    @confirm="handleDeleteVersion">
    <AuthButton
      action-id="package_manage"
      activ-bk-tooltips="{
        content: t('含有实例，无法删除'),
        disabled: !isAppliedInstance,
      }"
      class="ml-12"
      :disabled="isAppliedInstance"
      :loading="deleteDbVersionLoading"
      :permission="permission"
      :resource="dbType"
      size="small"
      text
      theme="primary">
      {{ t('删除') }}
    </AuthButton>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { deleteDbVersion } from '@services/source/version';

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

  const isAppliedInstance = computed(() => {
    const packages = props.data.packages;
    return Array.isArray(packages) && packages.length > 0 && packages.some((item) => item.instances > 0);
  });

  const { loading: deleteDbVersionLoading, run: runDeleteDbVersion } = useRequest(deleteDbVersion, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const handleDeleteVersion = () => {
    runDeleteDbVersion({
      id: props.data!.id,
    });
  };
</script>
