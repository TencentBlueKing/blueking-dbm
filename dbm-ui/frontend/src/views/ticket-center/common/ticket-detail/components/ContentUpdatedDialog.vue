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
  <BkDialog
    :is-show="isShow"
    :quick-close="false"
    :title="t('单据内容已更新')"
    :width="480"
    @closed="handleClose">
    <I18nT
      keypath="n_于_t_修改了本单据内容_刷新后可查看最新内容"
      scope="global">
      <bk-user-display-name :user-id="latestRecord?.operator" />
      <span>{{ latestRecord?.createAtDisplay }}</span>
    </I18nT>
    <template #footer>
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleRefresh">
        {{ t('刷新页面') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { Instance } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketModifyRecords, getTicketVersion } from '@services/source/ticket';

  import { isTicketModifiable } from '@views/ticket-center/common/ticket-modify/registry';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    data: TicketModel;
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 只有这些状态下单据内容可能被改
  const MODIFIABLE_STATUS: string[] = [
    TicketModel.STATUS_APPROVE,
    TicketModel.STATUS_CONFIRM_PENDING,
    TicketModel.STATUS_RESOURCE_REPLENISH,
  ];

  // 详情未返回版本表示还没改过单，按版本 0 比较
  const getBaseVersion = () => props.data.version ?? 0;

  const isShow = ref(false);
  const latestRecord = shallowRef<TicketModifyRecordModel>();
  // 已提示过的版本，同一版本只提示一次
  let notifiedVersion = getBaseVersion();
  // 弹窗期间暂停了点击外部关闭的气泡（如审批浮层）
  let pausedTippyList: Instance[] = [];
  // 卸载时可能还有请求在途，回调里不能再弹窗或续轮询，否则定时器无人清理
  let isUnmounted = false;

  const isWatching = computed(
    () => isTicketModifiable(props.data.ticket_type) && MODIFIABLE_STATUS.includes(props.data.status),
  );

  // 点弹窗按钮或关闭也是一次点击外部，弹窗期间不让已打开的气泡因此关闭，保留其中已填内容
  const pauseTippyHideOnClick = () => {
    pausedTippyList = Array.from(document.querySelectorAll<{ _tippy?: Instance } & HTMLElement>('[data-tippy-root]'))
      // eslint-disable-next-line no-underscore-dangle
      .map((item) => item._tippy)
      .filter((item): item is Instance => Boolean(item?.state.isVisible && item.props.hideOnClick === true));
    pausedTippyList.forEach((item) => item.setProps({ hideOnClick: false }));
  };

  const resumeTippyHideOnClick = () => {
    pausedTippyList.forEach((item) => item.setProps({ hideOnClick: true }));
    pausedTippyList = [];
  };

  const checkVersion = () => {
    getTicketVersion({
      ticket_ids: `${props.data.id}`,
    })
      .then((versionMap) => {
        if (isUnmounted || versionMap[props.data.id] === undefined) {
          return;
        }
        const version = versionMap[props.data.id] ?? 0;
        if (version === getBaseVersion() || version === notifiedVersion) {
          return;
        }
        notifiedVersion = version;
        return getTicketModifyRecords({ id: props.data.id }).then((recordList) => {
          if (isUnmounted) {
            return;
          }
          latestRecord.value = _.last(recordList);
          if (!isShow.value) {
            pauseTippyHideOnClick();
            isShow.value = true;
          }
        });
      })
      .finally(() => {
        if (!isUnmounted && isWatching.value) {
          startLoop();
        }
      });
  };

  const { start: startLoop, stop: stopLoop } = useTimeoutFn(checkVersion, 3000, {
    immediate: false,
  });

  watch(
    () => props.data,
    () => {
      notifiedVersion = getBaseVersion();
      stopLoop();
      if (isWatching.value) {
        startLoop();
      }
    },
    {
      immediate: true,
    },
  );

  const handleRefresh = () => {
    isShow.value = false;
    resumeTippyHideOnClick();
    emits('refresh');
  };

  // 右上角关闭不刷新，保留当前页面
  const handleClose = () => {
    isShow.value = false;
    resumeTippyHideOnClick();
  };

  onBeforeUnmount(() => {
    isUnmounted = true;
  });
</script>
