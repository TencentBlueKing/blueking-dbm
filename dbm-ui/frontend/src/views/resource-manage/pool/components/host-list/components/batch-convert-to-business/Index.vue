<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->
<template>
  <ReviewDataDialog
    :is-show="isShow"
    :loading="isUpdating"
    :selected="selectedIpList"
    :tip="t('确认后，主机将标记为业务专属')"
    :title="t('确认批量将 {n} 台主机转入业务资源池？', { n: props.selected.length })"
    @cancel="handleCancel"
    @confirm="handleConfirm" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { updateResource } from '@services/source/dbresourceResource';

  import { messageSuccess } from '@utils';

  import ReviewDataDialog from '../review-data-dialog/Index.vue';

  interface Props {
    selected: DbResourceModel[];
    bizId: number;
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

  const { loading: isUpdating, run: runUpdate } = useRequest(updateResource, {
    manual: true,
    onSuccess() {
      handleCancel();
      messageSuccess(t('设置成功'));
    },
  });

  const handleConfirm = () => {
    runUpdate({
      bk_host_ids: props.selected.map((item) => item.bk_host_id),
      for_biz: props.bizId,
      rack_id: props.selected[0].rack_id,
      resource_type: '',
      storage_device: props.selected[0].storage_device,
    });
  };

  const handleCancel = () => {
    emits('refresh');
    isShow.value = false;
  };
</script>

<style lang="scss" scoped></style>
