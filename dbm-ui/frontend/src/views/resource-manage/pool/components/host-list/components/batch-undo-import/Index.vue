<template>
  <ReviewDataDialog
    :is-show="isShow"
    :loading="isRemoving"
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

  import { messageSuccess } from '@utils';

  import ReviewDataDialog from '../review-data-dialog/Index.vue';

  interface Props {
    selected: DbResourceModel[];
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

  const { loading: isRemoving, run: runDelete } = useRequest(removeResource, {
    manual: true,
    onSuccess() {
      handleCancel();
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
    emits('refresh');
    isShow.value = false;
  };
</script>

<style lang="scss" scoped></style>
