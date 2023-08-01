<template>
  <BkDialog
    dialog-type="show"
    :draggable="false"
    height="auto"
    :is-show="props.isShow"
    quick-close
    :title="$t('账号信息')"
    :width="480"
    @closed="handleClose">
    <div class="account-details">
      <div class="account-details">
        <div
          v-for="column of accountColumns"
          :key="column.key"
          class="account-details__item">
          <div class="account-details__label">
            {{ column.label }}：
          </div>
          <div
            v-if="column.value"
            class="account-details__value">
            {{ column.value }}
            <BkButton
              text
              theme="primary"
              @click="updatePassword">
              {{ t('修改密码') }}
            </BkButton>
          </div>
          <div v-else>
            {{ props.info?.account?.[column.key] }}
          </div>
        </div>
        <div
          v-if="isDelete"
          class="account-details__item">
          <span class="account-details__label" />
          <span class="account-details__value">
            <BkButton
              hover-theme="danger"
              @click="handleDeleteAccount()">{{ $t('删除账号') }}</BkButton>
          </span>
        </div>
      </div>
    </div>
  </BkDialog>
</template>

<script setup lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import { deleteAccount } from '@services/permission';

  import { useInfoWithIcon } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import type { AccountColumn } from '../common/types';

  const props = defineProps({
    // eslint-disable-next-line vue/no-unused-properties
    isShow: {
      type: Boolean,
      default: false,
    },
    info: {
      type: Object,
      default() {
        return {};
      },
    },
  });
  const emits = defineEmits(['update:isShow', 'updatePassword', 'deleteAccount']);

  const { t } = useI18n();
  const globalbizsStore = useGlobalBizs();

  const bizId = computed(() => globalbizsStore.currentBizId);
  const isDelete = computed(() => !props.info?.rules?.length);

  const accountColumns: Array<AccountColumn> = [{
    label: t('账号名'),
    key: 'user',
  }, {
    label: t('密码'),
    key: 'password',
    value: '****************',
  }, {
    label: t('创建时间'),
    key: 'create_time',
  }, {
    label: t('创建人'),
    key: 'creator',
  }];

  const updatePassword = () => {
    emits('updatePassword');
  };

  function handleDeleteAccount() {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该账号'),
      content: t('即将删除账号xx_删除后将不能恢复', { name: props.info.account.user }),
      onConfirm: async () => {
        try {
          await deleteAccount(bizId.value, props.info.account.account_id);
          Message({
            message: t('成功删除账号'),
            theme: 'success',
            delay: 1500,
          });

          emits('deleteAccount');

          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }

  const handleClose = () => {
    emits('update:isShow', false);
  };
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.account-details {
  font-size: @font-size-mini;

  &__item {
    display: flex;
    padding-bottom: 16px;
  }

  &__label {
    width: 90px;
    text-align: right;
    flex-shrink: 0;
  }

  &__value {
    color: @title-color;
  }
}
</style>
