<template>
  <BkPopConfirm
    :confirm-config="{
      theme: 'danger',
      loading: deleteReleaseVersionLoading,
    }"
    :confirm-text="t('删除')"
    :content="t('删除操作无法撤回，请谨慎操作！')"
    :disabled="data?.isDeleteDisabled"
    placement="bottom"
    :title="t('确认删除该发型版？')"
    trigger="click"
    width="280"
    @confirm="handleDeleteRelease">
    <AuthTemplate
      action-id="package_manage"
      :permission="data?.permission.package_manage"
      :resource="dbType">
      <DbIcon
        v-bk-tooltips="{
          content: data?.isDeleteDisabled
            ? t('该发行版下存在 n 个版本，请删除后再操作', { n: data.dbversion_count })
            : t('删除'),
          disabled: !data?.isDeleteDisabled,
        }"
        class="edit-icon"
        :class="{ 'is-disabled': data?.isDeleteDisabled }"
        type="delete"
        @click.stop />
    </AuthTemplate>
  </BkPopConfirm>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ReleaseVersionModel from '@services/model/version-file/release-version';
  import { deleteReleaseVersion } from '@services/source/version';

  import { messageSuccess } from '@utils';

  interface Props {
    data?: ReleaseVersionModel;
    dbType: string;
    pkgType: string;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { loading: deleteReleaseVersionLoading, run: runDeleteReleaseVersion } = useRequest(deleteReleaseVersion, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('success');
    },
  });

  const handleDeleteRelease = () => {
    runDeleteReleaseVersion({
      db_type: props.dbType,
      id: props.data!.id,
      pkg_type: props.pkgType,
    });
  };
</script>
