<template>
  <ReviewDataDialog
    :is-show="isShow"
    :loading="loading"
    :selected="selectedIpList"
    :tip="t('确认后，主机将从资源池移回原有模块')"
    :title="title"
    @cancel="handleCancel"
    @confirm="handleConfirm" />
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { removeResource } from '@services/source/dbresourceResource';

  import ReviewDataDialog from '@components/review-data-dialog/Index.vue';

  interface Props {
    selected: Array<DbResourceModel>;
    refresh: () => void;
  }
  const props = defineProps<Props>();
  const isShow = defineModel('isShow', {
    default: true,
    type: Boolean,
  });

  const { t } = useI18n();

  const selectedIpList = computed(() => props.selected.map((v) => v.ip));
  const title = computed(() => t('确认批量撤销 {n} 台主机的导入?', { n: props.selected.length }));

  const { loading, run: runDelete } = useRequest(removeResource, {
    manual: true,
    onSuccess: () => {
      props.refresh();
      isShow.value = false;
      Message({
        message: t('转入成功'),
        theme: 'success',
      });
    },
  });

  const handleConfirm = () => {
    runDelete({
      bk_host_ids: props.selected.map((v) => v.bk_host_id),
      event: 'undo_import',
    });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="scss" scoped></style>
