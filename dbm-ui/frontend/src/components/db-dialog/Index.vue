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
  <BkDialog
    v-bind="{ ...attrs, ...scopeIdAttrs }"
    :before-close="beforeCloseCallback"
    :cancel-text="cancelText || undefined"
    :confirm-text="confirmText || undefined"
    :is-show="isShow"
    @update:is-show="handleUpdateShow">
    <template
      v-if="slots.header"
      #header>
      <slot name="header" />
    </template>
    <!-- 与 BkDialog 保持一致：没有默认插槽时不渲染内容区容器 -->
    <template
      v-if="slots.default"
      #default>
      <slot />
    </template>
    <template
      v-if="slots.footer || showFooter"
      #footer>
      <slot name="footer">
        <BkButton
          v-if="showConfirm"
          v-bk-tooltips="submitButtonDisabledInfo.tooltips"
          class="mr-8"
          :disabled="submitButtonDisabledInfo.disabled"
          :loading="isLoading"
          style="min-width: 64px"
          theme="primary"
          @click="handleConfirm">
          {{ confirmText || t('确定') }}
        </BkButton>
        <BkButton
          style="min-width: 64px"
          @click="handleCancle">
          {{ cancelText || t('取消') }}
        </BkButton>
      </slot>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useModelProvider } from '@hooks';

  import { leaveConfirm, markCoveredPageChanged, popoverInjectKey, registerOpenedPopover } from '@utils';

  interface Props {
    /**
     * 调用方自己的关闭前检查（点关闭图标、按 Esc、点遮罩时执行），返回 true 才关闭。
     * 传了就由它决定是否允许关闭，组件不再叠加自己的离开确认，避免弹两次。
     * 声明成 prop 是因为模板里 :before-close 写在 v-bind="attrs" 之后，走 attrs 会被覆盖
     */
    beforeClose?: () => unknown;
    cancelText?: string;
    confirmText?: string;
    disabledConfirm?: boolean | string;
    // 与 BkDialog 保持一致为可选，调用方 defineModel 不带默认值时类型是 boolean | undefined
    isShow?: boolean;
    showConfirm?: boolean;
    /**
     * 是否渲染本组件的默认底部（确定、取消）。不传 footer 插槽且为 false 时不接管底部，
     * 由 BkDialog 按 dialog-type 自行决定（默认 operation 会渲染它自己的确定、取消）
     */
    showFooter?: boolean;
    showLeaveConfirm?: boolean;
  }

  type Emits = (e: 'update:isShow', isShow: boolean) => void;
  interface Exposes {
    /**
     * 关闭前检查，返回是否允许关闭：内容编辑过时弹离开确认，确认离开后还原页面状态。
     * 自写 #footer 的取消按钮先 await 它，再执行自己的关闭逻辑
     */
    beforeClose: () => boolean | Promise<boolean>;
    handleCancle: () => void;
    handleConfirm: () => void;
  }

  defineOptions({
    inheritAttrs: false,
  });

  const props = withDefaults(defineProps<Props>(), {
    beforeClose: undefined,
    cancelText: '',
    confirmText: '',
    disabledConfirm: false,
    isShow: false,
    showConfirm: true,
    showFooter: false,
    showLeaveConfirm: true,
  });

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  const attrs = useAttrs();
  const slots = useSlots();
  const currentInstance = getCurrentInstance();

  const isLoading = ref(false);
  // 弹窗打开时页面的离开确认状态
  let pageChangeConfirm: boolean | 'popover' = false;
  // 本实例是否处于打开状态（打开后尚未执行关闭兜底）
  let isOpened = false;
  // 在「被弹层遮住的已编辑页面」登记表里的 key
  const coveredPageKey = Symbol('db-dialog');
  // 注销本实例在打开中弹层登记表里的记录
  let unregisterOpenedPopover = () => {};

  // 告知弹窗内容的 DbForm / EditableTable 自己在弹层内
  provide(popoverInjectKey, true);

  /**
   * BkDialog 会把自身 vnode 的 scopeId 加到 teleport 出去的弹窗根节点上，
   * 包了一层后这个 scopeId 变成 DbDialog 的，这里把调用方的 scopeId 透传下去，
   * 保证调用方 scoped 样式里通过 class 命中弹窗根节点的写法继续生效。
   * attrs 不是响应式对象，不能放 computed 里，所以只预先算好 scopeId 部分，在模板里合并
   */
  const callerScopeId = currentInstance?.vnode.scopeId;
  const scopeIdAttrs = callerScopeId ? { [callerScopeId]: '' } : {};

  const submitButtonDisabledInfo = computed(() => {
    const info = {
      disabled: false,
      tooltips: {
        content: '',
        disabled: true,
      },
    };

    if (_.isString(props.disabledConfirm)) {
      info.disabled = true;
      info.tooltips.disabled = false;
      info.tooltips.content = props.disabledConfirm;
      return info;
    }

    info.disabled = !!props.disabledConfirm;
    return info;
  });

  // 弹窗内的编辑已确认离开或已提交：还原为打开前的页面状态
  const restorePageChangeConfirm = () => {
    unregisterOpenedPopover();
    window.changeConfirm = pageChangeConfirm;
    markCoveredPageChanged(coveredPageKey, false);
  };

  /**
   * 关闭兜底：调用方直接把 isShow 置为 false、或打开状态下被 v-if 卸载时，组件内部的还原走不到。
   * 不是 true 说明弹窗内容没被编辑（仍是 'popover'），或弹窗内的 DbForm / EditableTable 已随关闭卸载、
   * 提交成功后被置为 false，都还原为打开前的页面状态。
   * 已是 true（弹窗内容被编辑过且仍挂载）保持不动，与 DbSideslider 一致
   */
  const restoreUnchangedPageChangeConfirm = () => {
    // 本实例没打开过不处理，否则会改掉外层弹层置的 'popover'
    if (!isOpened) {
      return;
    }
    isOpened = false;
    unregisterOpenedPopover();
    markCoveredPageChanged(coveredPageKey, false);
    if (window.changeConfirm !== true) {
      restorePageChangeConfirm();
    }
  };

  /**
   * 打开时记录页面状态并置为 'popover'：
   * 弹窗内容被编辑（DbForm / EditableTable 置 true）才能和页面原本的 true、上次打开残留的 true 区分。
   * 页面原本已编辑时登记下来，关闭浏览器标签时仍会提示
   */
  watch(
    () => props.isShow,
    (isShow) => {
      if (isShow) {
        pageChangeConfirm = window.changeConfirm;
        window.changeConfirm = 'popover';
        markCoveredPageChanged(coveredPageKey, pageChangeConfirm === true);
        isOpened = true;
        // 打开期间页面被修改（如提交后回填页面表单）时，把记录的页面状态改为已编辑，关闭还原时不丢
        unregisterOpenedPopover();
        unregisterOpenedPopover = registerOpenedPopover(() => {
          pageChangeConfirm = true;
          markCoveredPageChanged(coveredPageKey, true);
        });
      }
    },
    {
      immediate: true,
    },
  );

  /**
   * 关闭兜底放在 post 阶段：render-directive 为 if 时，弹窗内容在本轮渲染中卸载，
   * 内部 DbForm 的 onBeforeUnmount 会把 changeConfirm 置为 false，必须在它之后还原
   */
  watch(
    () => props.isShow,
    (isShow) => {
      if (!isShow) {
        restoreUnchangedPageChangeConfirm();
      }
    },
    {
      flush: 'post',
    },
  );

  // 用 onUnmounted 而不是 onBeforeUnmount：子组件（DbForm）的卸载钩子先执行完，再还原
  onUnmounted(() => {
    restoreUnchangedPageChangeConfirm();
  });

  // 打开后弹窗内容被编辑过才需要离开确认（打开时已置为 'popover'，只有内容被编辑才会变成 true）
  const isContentChanged = () => props.showLeaveConfirm && window.changeConfirm === true;

  // 离开确认，确认离开后还原为打开前的页面状态（leaveConfirm 确认时会置为 false）
  const confirmLeave = () =>
    leaveConfirm().then(() => {
      restorePageChangeConfirm();
      return true;
    });

  // 点关闭图标、按 Esc、点遮罩：内容未编辑时直接关闭，与 BkDialog 一致；取消离开时返回 false 阻止关闭
  const beforeCloseCallback = () => {
    if (props.beforeClose) {
      return Promise.resolve(props.beforeClose()).then((result) => {
        if (result) {
          restorePageChangeConfirm();
        }
        // 与 BkDialog 一致：只有 true 才关闭
        return !!result;
      });
    }
    if (!isContentChanged()) {
      return true;
    }
    return confirmLeave().catch(() => false);
  };

  const close = () => {
    emit('update:isShow', false);
  };

  const handleUpdateShow = () => {
    close();
  };

  const getModelProvier = useModelProvider();

  // 确定
  const handleConfirm = () => {
    isLoading.value = true;
    const { submit } = getModelProvier();
    submit()
      .then(() => {
        restorePageChangeConfirm();
        close();
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  // 取消
  const handleCancle = () => {
    const { cancel } = getModelProvier();
    if (!isContentChanged()) {
      return Promise.resolve(cancel()).then(() => {
        restorePageChangeConfirm();
        close();
      });
    }

    return (
      confirmLeave()
        .then(() => cancel())
        .then(() => close())
        // 离开确认点了取消：保持打开，吞掉 leaveConfirm 的 reject，避免未处理的 Promise 异常
        .catch(() => {})
    );
  };

  defineExpose<Exposes>({
    beforeClose: beforeCloseCallback,
    handleCancle,
    handleConfirm,
  });
</script>
