<template>
  <BkDialog
    dialog-type="show"
    :draggable="false"
    :is-show="isShow"
    quick-close
    :title="t('账号信息')"
    :width="480"
    @closed="handleClose">
    <div class="mongo-account-details">
      <div class="mongo-account-details">
        <div
          v-for="column of accountColumns"
          :key="column.key"
          class="details-item">
          <div class="details-label">{{ column.label }}：</div>
          <div class="details-value">
            {{ column.value ?? props.data.account[column.key] }}
          </div>
        </div>
        <div
          v-if="isDelete"
          class="details-item">
          <span class="details-label" />
          <span class="details-value">
            <BkButton
              hover-theme="danger"
              @click="handleDeleteAccount()">
              {{ t('删除账号') }}
            </BkButton>
          </span>
        </div>
      </div>
    </div>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { PermissionRule, PermissionRuleAccount } from '@services/types';

  interface Props {
    data: PermissionRule;
  }

  type Emits = (e: 'deleteAccount', row: PermissionRule) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
    required: true,
  });

  const { t } = useI18n();

  const accountColumns: Array<{
    key: keyof PermissionRuleAccount;
    label: string;
    value?: string;
  }> = [
    {
      key: 'user',
      label: t('账号名'),
    },
    {
      key: 'password',
      label: t('密码'),
      value: '****************',
    },
    {
      key: 'create_time',
      label: t('创建时间'),
    },
    {
      key: 'creator',
      label: t('创建人'),
    },
  ];

  const isDelete = computed(() => !props.data.rules.length);

  const handleDeleteAccount = () => {
    emits('deleteAccount', props.data);
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .mongo-account-details {
    font-size: @font-size-mini;

    .details-item {
      display: flex;
      padding-bottom: 16px;
    }

    .details-label {
      width: 90px;
      text-align: right;
      flex-shrink: 0;
    }

    .details-value {
      color: @title-color;
    }
  }
</style>
