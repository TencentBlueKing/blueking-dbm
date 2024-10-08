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
  <BkPopConfirm
    ext-cls="host-operation-btn"
    :title="title"
    trigger="click"
    width="360"
    @confirm="handleConfirm">
    <slot />
    <template #content>
      <div class="content">
        <div>
          <span>{{ t('主机') }}：</span>
          <span class="ip">{{ data.ip }}</span>
        </div>
        <div class="tip">{{ tip }}</div>
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { removeResource, updateResource } from '@services/source/dbresourceResource';

  import { useGlobalBizs } from '@stores';

  import { messageSuccess } from '@utils';

  interface Props {
    title: string;
    tip: string;
    data: DbResourceModel;
    type: ServiceParameters<typeof removeResource>['event'] | 'to_biz' | 'to_public';
  }

  interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const { run: runRemove } = useRequest(removeResource, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('refresh');
    },
  });

  const { run: convertToPublic } = useRequest(updateResource, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('refresh');
    },
  });

  const handleConfirm = () => {
    if (['to_public', 'to_biz'].includes(props.type)) {
      convertToPublic({
        bk_host_ids: [props.data.bk_host_id],
        for_biz: props.type === 'to_biz' ? globalBizsStore.currentBizId : 0,
        rack_id: '',
        resource_type: props.data.resource_type,
        storage_device: {},
      });
      return;
    }
    runRemove({
      bk_host_ids: [props.data.bk_host_id],
      event: props.type,
    });
  };
</script>

<style lang="less">
  .host-operation-btn {
    .content {
      font-size: 12px;
      color: #63656e;

      .ip {
        color: #313238;
      }

      .tip {
        margin-top: 4px;
        margin-bottom: 14px;
      }
    }

    .bk-pop-confirm-title {
      font-size: 16px !important;
      color: #313238 !important;
    }
  }
</style>
