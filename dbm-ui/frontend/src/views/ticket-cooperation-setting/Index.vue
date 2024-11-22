<template>
  <div class="ticket-cooperation-setting">
    <DbCard
      mode="collapse"
      :title="t('单据协助')">
      <BkForm
        ref="formRef"
        :model="formModel">
        <BkFormItem :label="t('单据协助')">
          <BkSwitcher
            v-model="isCooperationOpen"
            class="mr-8"
            theme="primary" />
          {{ t('开启后，您指定的协作人将能够协助处理单据执行、继续任务等事项，同时也会收到单据通知') }}
        </BkFormItem>
        <BkFormItem
          v-if="isCooperationOpen"
          :label="t('默认协作人')"
          property="members"
          required>
          <MemberSelector v-model="formModel.members" />
        </BkFormItem>
      </BkForm>
    </DbCard>
    <BkButton
      class="submit-btn"
      :loading="isUpdating"
      theme="primary"
      @click="handleSubmit">
      {{ t('保存') }}
    </BkButton>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizSettingList, updateBizSetting } from '@services/source/bizSetting';

  import { useGlobalBizs } from '@stores';

  import MemberSelector from '@components/db-member-selector/index.vue';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();

  const formRef = useTemplateRef('formRef');
  const globalBizsStore = useGlobalBizs();

  const isCooperationOpen = ref(false);

  const formModel = reactive({
    members: [],
  });

  // 是否开启单据协助
  useRequest(getBizSettingList, {
    onSuccess: (data) => {
      isCooperationOpen.value = data.BIZ_ASSISTANCE_SWITCH;
    },
    defaultParams: [
      {
        bk_biz_id: globalBizsStore.currentBizId,
        key: 'BIZ_ASSISTANCE_SWITCH',
      },
    ],
  });

  // 获取默认协作人
  useRequest(getBizSettingList, {
    onSuccess: (data) => {
      formModel.members = data.BIZ_ASSISTANCE_VARS || [];
    },
    defaultParams: [
      {
        bk_biz_id: globalBizsStore.currentBizId,
        key: 'BIZ_ASSISTANCE_VARS',
      },
    ],
  });

  const { runAsync: runUpdate, loading: isUpdating } = useRequest(updateBizSetting, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('保存成功'));
    },
  });

  const handleSubmit = async () => {
    if (isCooperationOpen.value) {
      await formRef.value!.validate();
    }
    Promise.all([
      runUpdate({
        bk_biz_id: globalBizsStore.currentBizId,
        key: 'BIZ_ASSISTANCE_SWITCH',
        value: isCooperationOpen.value,
      }),
      runUpdate({
        bk_biz_id: globalBizsStore.currentBizId,
        key: 'BIZ_ASSISTANCE_VARS',
        value: formModel.members,
      }),
    ]);
  };
</script>

<style scoped lang="less">
  .ticket-cooperation-setting {
    .submit-btn {
      width: 88px;
      margin-top: 16px;
    }
  }
</style>
