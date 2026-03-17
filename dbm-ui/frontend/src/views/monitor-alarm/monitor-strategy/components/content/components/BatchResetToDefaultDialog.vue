<template>
  <BkDialog
    v-model:is-show="moduleValue"
    class="batch-reset-to-default-dialog"
    quick-close
    :title="t('批量恢复默认')"
    :width="500">
    <!-- <template #header>
      <span class="main-title">{{ t('批量恢复默认') }}</span>
      <span class="sub-title">{{ t('生效 n 条策略', { n: validCount }) }}</span>
    </template> -->
    <div class="text-box">
      <I18nT
        class="valid-confirm"
        keypath="确认将选中的 n 条自定义策略恢复为全局策略的默认配置？"
        scope="global"
        tag="span">
        <template #n>
          <span class="valid-count">{{ validCount }}</span>
        </template>
      </I18nT>
      <div class="valid-info mt-8">
        {{ t('恢复后，这些策略的自定义修改将被覆盖，重新跟随全局策略更新。此操作不可撤销。') }}
      </div>
      <BkAlert
        v-if="invalidCount"
        class="mt-8"
        theme="warning"
        :title="t('已自动过滤 n 条不适用的策略（内置策略或子策略），不受本次操作影响。', { n: invalidCount })" />
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { patchDeletePolicy } from '@services/source/monitor';

  import { messageSuccess } from '@utils';

  interface Props {
    selected: MonitorPolicyModel[];
  }

  type Emits = (e: 'suceess') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const moduleValue = defineModel<boolean>();

  const { t } = useI18n();

  const { loading: isSubmitting, run: runPatchDeletePolicy } = useRequest(patchDeletePolicy, {
    manual: true,
    onSuccess() {
      messageSuccess(t('批量恢复默认成功'));
      moduleValue.value = false;
      emits('suceess');
    },
  });

  const validList = computed(() => props.selected.filter((item) => item.isCustom));
  const validCount = computed(() => validList.value.length);
  const invalidCount = computed(() => props.selected.length - validCount.value);

  const handleSubmit = () => {
    runPatchDeletePolicy({ ids: validList.value.map((item) => item.id) });
  };

  const handleCancel = () => {
    moduleValue.value = false;
  };
</script>

<style lang="less">
  .batch-reset-to-default-dialog {
    .sub-title {
      padding-left: 8px;
      margin-left: 8px;
      font-size: 14px;
      color: #979ba5;
      border-left: 1px solid #dcdee5;
    }

    .text-box {
      // font-size: 14px;

      .valid-confirm {
        color: #313238;
      }

      .valid-count {
        color: #3a84ff;
      }

      .valid-info {
        padding: 12px 16px;
        color: #4d4f56;
        background-color: #f5f7fa;
      }
    }
  }
</style>
