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
  <div
    v-if="renderData"
    class="render-action-tag">
    <span ref="rootRef">
      <BkTag :theme="renderData.theme">
        {{ renderData.text }}
      </BkTag>
    </span>
    <I18nT
      ref="popRef"
      keypath="xx_跳转_单据_查看进度"
      style="font-size: 12px; line-height: 16px; color: #63656e"
      tag="div">
      <span>{{ renderData.tip }}</span>
      <AuthRouterLink
        v-if="isShown"
        action-id="ticket_view"
        :resource="data.ticket_id"
        target="_blank"
        :to="{
          name: 'SelfServiceMyTickets',
          query: {
            id: data.ticket_id,
          },
        }">
        {{ t('单据') }}
      </AuthRouterLink>
    </I18nT>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      action: 'delete' | 'change';
      ticket_id: number;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const actionMap = {
    delete: {
      tip: t('权限规则_t_任务正在进行中', { t: t('删除') }),
      text: t('删除中'),
      theme: 'danger',
    },
    change: {
      tip: t('权限规则_t_任务正在进行中', { t: t('修改') }),
      text: t('编辑中'),
      theme: 'warning',
    },
  } as Record<string, { tip: string; text: string; theme: 'danger' | 'warning' }>;

  const rootRef = ref();
  const popRef = ref();
  const isShown = ref(false);
  let tippyIns: Instance;

  const renderData = computed(() => actionMap[props.data.action]);

  const destroyInst = () => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  };

  watch(
    renderData,
    () => {
      if (renderData.value) {
        destroyInst();
        nextTick(() => {
          tippyIns = tippy(rootRef.value as SingleTarget, {
            content: popRef.value.$el,
            placement: 'top',
            appendTo: () => document.body,
            theme: 'light',
            maxWidth: 'none',
            interactive: true,
            arrow: true,
            offset: [0, 8],
            zIndex: 999999,
            hideOnClick: true,
            onShow() {
              isShown.value = true;
            },
            onHide() {
              isShown.value = false;
            },
          });
        });
      }
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    destroyInst();
  });
</script>
<style lang="less" scoped>
  .render-action-tag {
    display: inline-block;
  }
</style>
