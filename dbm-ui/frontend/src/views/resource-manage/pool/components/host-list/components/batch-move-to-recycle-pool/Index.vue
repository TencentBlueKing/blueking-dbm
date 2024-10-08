<template>
  <ReviewDataDialog
    :is-show="isShow"
    :loading="isRemoving"
    :selected="selectedIpList"
    :tip="t('确认后，主机将标记为待回收，等待处理')"
    :title="t('确认批量将 {n} 台主机转入回收池？', { n: props.selected.length })"
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
      emits('refresh');
      isShow.value = false;
      messageSuccess(t('设置成功'));
    },
  });

  const handleConfirm = () => {
    runDelete({
      bk_host_ids: props.selected.map((item) => item.bk_host_id),
      event: 'to_recycle',
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="scss" scoped></style>
