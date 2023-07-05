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
  <div style="padding-top: 208px;">
    <RenderSuccess :steps="steps">
      <template #title>
        {{ $t('整机替换提交成功') }}
      </template>
      <I18nT
        keypath="接下来您可以通过xx查看任务最新动态"
        tag="span">
        <RouterLink
          target="_blank"
          :to="{
            name: 'SelfServiceMyTickets',
            query: {
              filterId: ticketId,
            },
          }">
          {{ $t('我的服务单') }}
        </RouterLink>
      </I18nT>
      <template #action>
        <BkButton
          class="w88"
          theme="primary"
          @click="handleGoTicket">
          {{ $t('去看看') }}
        </BkButton>
        <BkButton
          class="ml8"
          @click="handleStepChange">
          {{ $t('继续提单') }}
        </BkButton>
      </template>
    </RenderSuccess>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import RenderSuccess from '@views/mysql/common/ticket-success/Index.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const { ticketId } = route.query;

  const steps = [
    {
      name: t('单据审批'),
    },
    {
      name: t('生产执行'),
    },
    {
      name: t('任务完成'),
    },
  ];

  const handleGoTicket = () => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        filterId: ticketId,
      },
    });
    window.open(route.href);
  };

  const handleStepChange = () => {
    router.push({
      name: 'RedisDBReplace',
    });
  };
</script>
