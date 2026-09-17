<template>
  <BkDialog
    v-model:is-show="moduleValue"
    class="operate-cluster-confirm-dialog"
    header-align="center"
    quick-close
    :width="480">
    <template #header>
      <span class="dialog-title">{{ title }}</span>
    </template>
    <div class="operate-cluster-confirm-content">
      <BkAlert
        v-if="tip"
        class="mb-12"
        theme="info"
        :title="tip" />
      <div class="confirm-summary">
        <span>{{ t('已选集群') }}：</span>
        <I18nT
          keypath="共 {n} 个，{action} {k}"
          tag="span">
          <template #n>
            <strong>{{ count.n }}</strong>
          </template>
          <template #action>{{ actionWord }}</template>
          <template #k>
            <strong>{{ count.k }}</strong>
          </template>
        </I18nT>
        <I18nT
          v-if="count.s > 0"
          keypath="，跳过 {s}"
          tag="span">
          <template #s>
            <span class="skip-num">{{ count.s }}</span>
          </template>
        </I18nT>
        <I18nT
          v-if="count.a > 0 && count.b > 0"
          keypath="（无权限 {a}，{reason} {b}）"
          tag="span">
          <template #a>{{ count.a }}</template>
          <template #b>{{ count.b }}</template>
          <template #reason>{{ reasonWord }}</template>
        </I18nT>
        <I18nT
          v-else-if="count.a > 0"
          keypath="（无权限 {a}）"
          tag="span">
          <template #a>{{ count.a }}</template>
        </I18nT>
        <I18nT
          v-else-if="count.b > 0"
          keypath="（{reason} {b}）"
          tag="span">
          <template #b>{{ count.b }}</template>
          <template #reason>{{ reasonWord }}</template>
        </I18nT>
      </div>
      <div class="confirm-list">
        <div class="list-title">{{ detailTitle }}</div>
        <div
          v-for="item in toOperate"
          :key="item.id"
          class="list-item">
          {{ item.master_domain }}
        </div>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!count.k"
        :theme="confirmButtonTheme"
        @click="handleConfirm">
        {{ confirmText }}
      </BkButton>
      <BkButton @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { BatchOperationCount } from '@utils';

  interface Props {
    /** 操作动作词，如“禁用”“启用”“删除” */
    actionWord: string;
    /** 确认按钮主题 */
    confirmButtonTheme: 'danger' | 'primary';
    /** 确认按钮文案 */
    confirmText: string;
    count: BatchOperationCount;
    /** 明细标题，如“将禁用的集群（{K}）” */
    detailTitle: string;
    /** 状态不符原因词，如“已禁用”“未禁用” */
    reasonWord: string;
    /** 操作提示文案 */
    tip?: string;
    /** 弹窗标题 */
    title: string;
    toOperate: { cluster_name: string; id: number; master_domain: string }[];
  }

  type Emits = (e: 'confirm') => void;

  withDefaults(defineProps<Props>(), {
    tip: '',
  });
  const emit = defineEmits<Emits>();
  const moduleValue = defineModel<boolean>('isShow');

  const { t } = useI18n();

  const handleConfirm = () => {
    emit('confirm');
  };

  const handleCancel = () => {
    moduleValue.value = false;
  };
</script>

<style lang="less">
  .dialog-title {
    font-size: 16px;
    font-weight: 700;
  }

  .operate-cluster-confirm-content {
    .confirm-summary {
      padding: 8px 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
      background-color: #f0f1f5;

      strong {
        font-weight: 700;
        color: #313238;
      }

      .skip-num {
        font-weight: 700;
        color: #ff9c01;
      }
    }

    .confirm-list {
      max-height: 240px;
      overflow-y: auto;
      border: 1px solid #eaebf0;
      border-top: none;

      .list-title {
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 700;
        color: #313238;
        background-color: #fff;
        border-bottom: 1px solid #f0f1f5;
      }

      .list-item {
        padding: 8px 12px;
        font-size: 12px;
        color: #63656e;
        border-bottom: 1px solid #f0f1f5;

        &:last-child {
          border-bottom: none;
        }
      }
    }
  }
</style>
