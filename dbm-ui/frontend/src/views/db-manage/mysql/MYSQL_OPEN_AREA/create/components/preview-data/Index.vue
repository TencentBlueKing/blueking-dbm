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
  <SmartAction>
    <DbDialog
      v-model:is-show="isShow"
      :confirm-button-disable-info="{ disabled: isExistedErrorMsg, tooltips: { content: '', disabled: true } }"
      :height="760"
      :title="t('请确认以下开区内容：')"
      :width="1536">
      <BkTable
        :data="tableData"
        :max-height="600">
        <BkTableColumn
          field="target_cluster_domain"
          :label="t('目标集群')"
          :width="300" />
        <BkTableColumn
          field="target_db"
          :label="t('新 DB')"
          :width="300" />
        <BkTableColumn
          field="data_tblist"
          :label="t('表结构')"
          :width="180">
          <template #default>
            {{ t('所有表') }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="schema_tblist"
          :label="t('表数据')"
          :width="180">
          <template #default="{ row }: { row: RowData }">
            <span v-if="row.schema_tblist.length === 0">--</span>
            <RenderTagOverflow
              v-else
              :data="_.flatMap(row.schema_tblist)" />
          </template>
        </BkTableColumn>
        <BkTableColumn :label="t('授权 IP')">
          <template #default="{ row }: { row: RowData }">
            {{ row.authorize_ips?.join(',') || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
      <template #footer>
        <AuthButton
          action-id="mysql_open_area"
          :resource="props.sourceClusterId"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </AuthButton>
        <BkButton
          class="ml-8"
          @click="isShow = false">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </DbDialog>
  </SmartAction>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getPreview } from '@services/source/openarea';

  import { useCreateTicket, useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import RenderTagOverflow from '@components/render-tag-overflow/Index.vue';

  type RowData = {
    target_cluster_domain: string;
  } & Props['data']['config_data'][0]['execute_objects'][0];

  interface Props {
    data: ServiceReturnType<typeof getPreview>;
    sourceClusterId: number;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow');

  const router = useRouter();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const tableData = shallowRef<RowData[]>([]);

  const isExistedErrorMsg = computed(() =>
    props.data?.config_data.some((item) => item.execute_objects.some((obj) => obj.error_msg)),
  );

  const { run: createTicketRun } = useCreateTicket<
    {
      cluster_id: number;
      force: boolean;
    } & Props['data']
  >(TicketTypes.MYSQL_OPEN_AREA, {
    onSuccess(ticketId) {
      ticketMessage(ticketId);
      window.changeConfirm = false;
      router.push({
        name: TicketTypes.MYSQL_OPEN_AREA,
      });
    },
  });

  watch(
    () => props.data,
    () => {
      if (props.data) {
        tableData.value = props.data.config_data.reduce<RowData[]>((acc, item) => {
          item.execute_objects.forEach((executeObjects) => {
            acc.push({
              target_cluster_domain: item.target_cluster_domain,
              ...executeObjects,
            });
          });
          return acc;
        }, []);
      }
    },
    {
      immediate: true,
    },
  );

  const handleSubmit = () =>
    createTicketRun({
      details: {
        cluster_id: props.sourceClusterId,
        force: false,
        ...props.data,
      },
    });
</script>
