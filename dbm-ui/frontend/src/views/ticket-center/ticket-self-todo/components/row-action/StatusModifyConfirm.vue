<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TableColumn
    col-key="row-operation"
    fixed="right"
    :min-width="100"
    :title="t('操作')">
    <template #default="{ row }: { row: TicketModel }">
      <BkButton
        text
        theme="primary"
        @click="() => handleConfirm(row)">
        {{ t('确认修改') }}
      </BkButton>
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { OPEN_CONFIRM_MODIFY } from '@views/ticket-center/common/ticket-modify/constants';

  import { getBusinessHref } from '@utils';

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
  const router = useRouter();

  // 新标签页打开单据详情，并直达打开确认修改抽屉
  const handleConfirm = (row: TicketModel) => {
    const { href } = router.resolve({
      name: 'ticketDetail',
      params: {
        ticketId: row.id,
      },
      query: {
        open: OPEN_CONFIRM_MODIFY,
      },
    });
    window.open(getBusinessHref(href, row.bk_biz_id));
  };
</script>
