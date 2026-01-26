<template>
  <BkSideslider
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    class="create-risk-slider-main"
    quick-close
    render-directive="if"
    :title="isSpecial ? t('新建要求') : t('新建风险')"
    :width="960"
    @closed="handleClosed">
    <BkForm
      ref="formRef"
      form-type="vertical"
      :model="formData"
      :rules="rules">
      <BkFormItem
        :label="isSpecial ? t('标题') : t('风险名称')"
        property="name"
        required>
        <BkInput
          v-model="formData.name"
          clearable
          :placeholder="isSpecial ? t('请输入标题') : t('请输入风险名称')" />
      </BkFormItem>
      <BkFormItem
        v-if="!isSpecial"
        :label="t('业务影响')"
        property="effectBizs"
        required>
        <BkSelect
          v-model="formData.effectBizs"
          filterable
          :list="effectBizLabels"
          multiple
          multiple-mode="tag"
          :placeholder="t('请选择影响')" />
      </BkFormItem>
      <BkFormItem
        :label="isSpecial ? t('涉及 DB') : t('影响 DB')"
        property="effectDb"
        required>
        <BkSelect
          v-model="formData.effectDb"
          filterable
          :list="dbList"
          :placeholder="isSpecial ? t('请选择 DB  类型') : t('请选择 DB')" />
      </BkFormItem>
      <BkFormItem
        class="effect-clusters-main"
        :label="isSpecial ? t('涉及集群') : t('影响集群')"
        property="effectClusters">
        <div style="display: flex">
          <BkSelect
            v-model="formData.effectClusters"
            :disabled="isSelectAllCluster"
            filterable
            :list="clusterList"
            multiple
            multiple-mode="tag"
            :placeholder="t('请选择集群')"
            style="flex: 1" />
          <BkCheckbox
            v-model="isSelectAllCluster"
            class="ml-12">
            {{ t('全部') }}
          </BkCheckbox>
        </div>
      </BkFormItem>
      <BkFormItem
        :label="isSpecial ? t('具体要求') : t('风险描述')"
        property="describe"
        required>
        <RiskMemoEditor
          v-model="formData.describe"
          class="rich-text-editor-main"
          :placeholder="isSpecial ? t('请输入具体的要求') : t('请输入风险描述')" />
      </BkFormItem>
    </BkForm>
    <div class="operate-main">
      <BkButton
        class="w-88"
        :loading="createLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleClickCancel">
        {{ t('取消') }}
      </BkButton>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { filterClusters } from '@services/source/dbbase';
  import { createRiskMemo } from '@services/source/riskMemo';

  import { useBeforeClose } from '@hooks';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import RiskMemoEditor from '../../RickMemoEditor.vue';

  interface Props {
    effectBizLabels?: {
      label: string;
      value: string;
    }[];
    isSpecial?: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    effectBizLabels: () => [],
    isSpecial: false,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const initFormData = () => ({
    describe: '',
    effectBizs: [] as string[],
    effectClusters: [] as string[],
    effectDb: '',
    name: '',
  });

  const { t } = useI18n();
  const handleBeforeClose = useBeforeClose();

  const formRef = ref<any>(null);
  const formData = ref(initFormData());
  const isSelectAllCluster = ref(false);
  const clusterList = ref<Props['effectBizLabels']>([]);

  const dbList = Object.values(DBTypeInfos).map((item) => ({
    label: item.name,
    value: item.id,
  }));

  const EMPTY_TEXT = '<p><br></p>';

  const rules = {
    describe: [
      {
        message: () => (props.isSpecial ? t('具体要求不能为空') : t('风险描述不能为空')),
        trigger: 'blur',
        validator: (value: string) => value !== EMPTY_TEXT,
      },
    ],
    effectClusters: [
      {
        message: () => (props.isSpecial ? t('涉及集群不能为空') : t('影响集群不能为空')),
        trigger: 'blur',
        validator: (list: string[]) => isSelectAllCluster.value || list.length > 0,
      },
    ],
  };

  const { run: runFilterClusters } = useRequest(filterClusters, {
    manual: true,
    onSuccess: (data) => {
      clusterList.value = data.map((item) => ({
        label: item.master_domain,
        value: item.master_domain,
      }));
    },
  });

  const { loading: createLoading, run: runCreateRiskMemo } = useRequest(createRiskMemo, {
    manual: true,
    onSuccess: () => {
      emits('success');
      handleClosed();
      isShow.value = false;
    },
  });

  watch(
    () => formData.value.effectDb,
    () => {
      if (formData.value.effectDb) {
        formData.value.effectClusters = [];
        isSelectAllCluster.value = false;
        runFilterClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          db_type: formData.value.effectDb as DBTypes,
        });
      }
    },
  );

  watch(
    formData,
    () => {
      Object.values(formData.value).forEach((item) => {
        if (item.length && item !== EMPTY_TEXT) {
          window.changeConfirm = true;
        }
      });
    },
    {
      deep: true,
    },
  );

  watch(isSelectAllCluster, () => {
    if (isSelectAllCluster.value) {
      formData.value.effectClusters = [];
    }
  });

  const handleConfirm = async () => {
    await formRef.value.validate();
    const params = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      db_type: formData.value.effectDb,
      description: formData.value.describe,
      inpact_cluster: isSelectAllCluster.value ? 'all' : formData.value.effectClusters.join(','),
      is_special: props.isSpecial,
      level: 'Middle',
      name: formData.value.name,
      status: 'backlog' as const,
    };
    if (!props.isSpecial) {
      Object.assign(params, {
        biz_inpact: formData.value.effectBizs.join(','),
      });
    }
    runCreateRiskMemo(params);
  };

  const handleClickCancel = () => {
    isShow.value = false;
    handleClosed();
  };

  const handleClosed = () => {
    window.changeConfirm = false;
    isSelectAllCluster.value = false;
    formData.value = initFormData();
  };
</script>
<style lang="less">
  .create-risk-slider-main {
    .bk-sideslider-content {
      padding: 18px 24px;

      .operate-main {
        display: flex;
        gap: 8px;
        margin-top: 32px;
      }
    }

    .effect-clusters-main {
      .bk-form-label {
        &::after {
          position: absolute;
          top: 0;
          width: 14px;
          color: #ea3636;
          text-align: center;
          content: '*';
        }
      }
    }

    .w-e-text-placeholder {
      top: 8px;
    }
  }
</style>
