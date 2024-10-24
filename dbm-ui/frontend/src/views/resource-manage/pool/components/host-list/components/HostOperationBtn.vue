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
    ext-cls="content-wrapper"
    :title="props.title"
    trigger="click"
    width="360"
    @confirm="handleConfirm">
    <BkButton
      :class="btnCls"
      text
      theme="primary">
      {{ buttonText }}
    </BkButton>
    <template #content>
      <section class="content">
        <div>
          <span>{{ t('主机') }}：</span>
          <span class="ip">{{ props.data.ip }}</span>
        </div>
        <div class="tip">{{ props.tip }}</div>
      </section>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { type DeleteEvent, removeResource } from '@services/source/dbresourceResource';

  interface Props {
    title: string;
    buttonText: string;
    tip: string;
    btnCls?: string;
    data: DbResourceModel;
    type: DeleteEvent;
    refresh: () => void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { run } = useRequest(removeResource, {
    manual: true,
    onSuccess: () => {
      Message({
        theme: 'success',
        message: t('操作成功'),
      });
      props.refresh();
    },
  });

  const handleConfirm = () => {
    run({
      bk_host_ids: [props.data.bk_host_id],
      event: props.type,
    });
  };
</script>

<style lang="less">
  .content-wrapper {
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
