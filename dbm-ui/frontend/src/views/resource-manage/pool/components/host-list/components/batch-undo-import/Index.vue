<template>
  <ReviewDataDialog
    :is-show="isShow"
    :loading="loading"
    :selected="selectedIpList"
    :tip="t('确认后，主机将从资源池移回原有模块')"
    :title="t('确认批量撤销 {n} 台主机的导入?', { n: props.selected.length })"
    @cancel="handleCancel"
    @confirm="handleConfirm" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { removeResource } from '@services/source/dbresourceResource';

  import ReviewDataDialog from '@components/review-data-dialog/Index.vue';

  import { messageSuccess } from '@utils';

  interface Props {
    selected: Array<DbResourceModel>;
  }

  interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: true,
  });

  const { t } = useI18n();

  const selectedIpList = computed(() => props.selected.map((item) => item.ip));

  const { loading, run: runDelete } = useRequest(removeResource, {
    manual: true,
    onSuccess: () => {
      emits('refresh');
      isShow.value = false;
      messageSuccess(t('设置成功'));
    },
  });

  const handleConfirm = () => {
    runDelete({
      bk_host_ids: props.selected.map((item) => item.bk_host_id),
      event: 'undo_import',
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="scss" scoped></style>
