<template>
  <ReviewDataDialog
    v-model:is-show="isShow"
    :confirm-handler="handleConfirm"
    :selected="selectedIpList"
    show-remark
    :tip="t('确认后，主机将标记为故障，等待处理')"
    :title="t('确认批量将 {n} 台主机转入故障池?', { n: props.selected.length })"
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

  const handleConfirm = ({ remark }: { remark: string }) => {
    return removeResource({
      event: 'to_fault',
      hosts: props.selected.map((item) => ({
        bk_biz_id: item.bk_biz_id,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        ip: item.ip,
      })),
      remark,
    });
  };

  const handleSuccess = () => {
    emits('refresh');
  };
</script>
