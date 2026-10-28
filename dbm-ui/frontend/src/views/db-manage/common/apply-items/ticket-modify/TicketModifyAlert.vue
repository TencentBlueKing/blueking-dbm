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

<!-- 改单模式的页面级 UI：顶部 Alert 与提交前的确认弹窗，改单模式下每个申请页都会渲染 -->
<template>
  <template v-if="modifyState">
    <div class="ticket-modify-alert">
      <BkAlert :theme="alertConfig.theme">
        <template #title>
          <span class="ticket-modify-alert-mode">{{ alertConfig.modeText }}</span>
          <!-- I18nT 插槽内的 v-if 会留下注释节点占住 {0}，带提单人与不带提单人的文案分开渲染 -->
          <I18nT
            v-if="alertConfig.withCreator"
            :keypath="alertConfig.keypath"
            scope="global">
            <bk-user-display-name :user-id="modifyState.ticketData.value?.creator" />
            <a
              :href="ticketDetailHref"
              target="_blank">
              {{ ticketId }}
            </a>
          </I18nT>
          <I18nT
            v-else
            :keypath="alertConfig.keypath"
            scope="global">
            <a
              :href="ticketDetailHref"
              target="_blank">
              {{ ticketId }}
            </a>
          </I18nT>
        </template>
      </BkAlert>
    </div>
    <BkDialog
      :is-show="modifyState.confirmState.isShow"
      :quick-close="false"
      :title="t('确认提交')"
      :width="800"
      @closed="() => handleClose(false)">
      <div class="ticket-modify-confirm-tip">
        {{ t('共n项变更，请确认后提交', { n: modifyState.confirmState.diffList.length }) }}
      </div>
      <DiffTable :data="modifyState.confirmState.diffList" />
      <div
        v-if="modifyState.mode !== TicketModifyRecordModel.MODE_RE_EDIT"
        class="ticket-modify-confirm-remark">
        <span class="ticket-modify-confirm-remark-label">{{ t('修改说明：') }}</span>
        <span>{{ modifyState.modifyRemark.value }}</span>
      </div>
      <template #footer>
        <BkButton
          class="w-88"
          theme="primary"
          @click="() => handleClose(true)">
          {{ modifyState.submitText }}
        </BkButton>
        <BkButton
          class="w-88 ml-8"
          @click="() => handleClose(false)">
          {{ t('取消') }}
        </BkButton>
      </template>
    </BkDialog>
  </template>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModifyRecordModel from '@services/model/ticket/modify-record';

  import { useTicketModifyState } from '@hooks';

  import DiffTable from '@views/ticket-center/common/ticket-modify/DiffTable.vue';

  import { getBusinessHref } from '@utils';

  const { t } = useI18n();
  const router = useRouter();
  const modifyState = useTicketModifyState();

  const ticketId = computed(() => modifyState?.ticketData.value?.id);

  const ticketDetailHref = computed(() => {
    const ticketData = modifyState?.ticketData.value;
    if (!ticketData) {
      return '';
    }
    const { href } = router.resolve({
      name: 'ticketDetail',
      params: {
        ticketId: ticketData.id,
      },
    });
    return getBusinessHref(href, ticketData.bk_biz_id);
  });

  const alertConfig = computed(() => {
    if (modifyState?.mode === TicketModifyRecordModel.MODE_RE_EDIT) {
      return {
        keypath: '您正在重新编辑单据n_重新提交后需重新审批',
        modeText: t('重新编辑：'),
        theme: 'info' as const,
        withCreator: false,
      };
    }
    if (modifyState?.mode === TicketModifyRecordModel.MODE_ADJUST_APPLY) {
      return {
        keypath: '您正在调整单据n的资源申请条件_提交后按新条件重新申领',
        modeText: t('调整申请：'),
        theme: 'warning' as const,
        withCreator: false,
      };
    }
    if (modifyState?.isSelfOnBehalf.value) {
      return {
        keypath: '您正在修改自己提交的单据n_提交后自动确认',
        modeText: t('代为修改：'),
        theme: 'warning' as const,
        withCreator: false,
      };
    }
    return {
      keypath: '您正在为n修改单据n_提交后需提单人确认',
      modeText: t('代为修改：'),
      theme: 'warning' as const,
      withCreator: true,
    };
  });

  const handleClose = (isConfirmed: boolean) => {
    if (!modifyState) {
      return;
    }
    modifyState.confirmState.isShow = false;
    modifyState.confirmState.resolve?.(isConfirmed);
    modifyState.confirmState.resolve = undefined;
  };
</script>
<style lang="less">
  // 模式说明条随页面滚动始终吸顶，提示当前处于改单模式
  // 外层容器带页面底色和四周留白，盖住下方滚动内容；
  // 内容区 .db-navigation-content-wrapper 有 20px 24px 0 的内边距，用负 margin / 负 top 抵掉，
  // 让吸顶后的容器贴住滚动区顶边、背景横向撑满，未滚动时 Alert 位置与原来一致
  .ticket-modify-alert {
    position: sticky;
    top: -20px;
    z-index: 10;
    padding: 20px 24px;
    margin: -20px -24px 0;
    background: @bg-gray;
  }

  .ticket-modify-alert-mode {
    font-weight: bold;
  }

  .ticket-modify-confirm-tip {
    margin-bottom: 16px;
    font-size: 12px;
    color: #63656e;
  }

  .ticket-modify-confirm-remark {
    margin-top: 16px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
    word-break: break-all;
    white-space: pre-wrap;

    .ticket-modify-confirm-remark-label {
      color: #4d4f56;
    }
  }
</style>
