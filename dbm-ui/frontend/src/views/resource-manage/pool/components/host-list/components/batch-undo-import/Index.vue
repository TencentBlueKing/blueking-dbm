<template>
  <ReviewDataDialog
    v-model:is-show="isShow"
    :alert="t('仅新导入且无被申请、转移等使用事件的主机，可执行撤销导入')"
    :confirm-handler="handleConfirm"
    :selected="selectedIpList"
    :tip="t('确认后，主机将从资源池删除，同时 CMDB 位置回到来源业务的空闲机模块')"
    :title="t('确认批量撤销 {n} 台主机的导入?', { n: props.selected.length })"
    @success="handleSuccess" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { removeResource } from '@services/source/dbresourceResource';

  import ReviewDataDialog from '../review-data-dialog/Index.vue';

  interface Props {
    selected: DbResourceModel[];
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: true,
  });

  const { t } = useI18n();

  const selectedIpList = computed(() => props.selected.map((item) => item.ip));

  const handleConfirm = () => {
    return removeResource({
      event: 'undo_import',
      hosts: props.selected.map((item) => ({
        bk_biz_id: item.bk_biz_id,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
      })),
    });
  };

  const handleSuccess = () => {
    emits('refresh');
  };
</script>
