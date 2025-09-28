<template>
  <Teleport
    v-if="isEditMode"
    to="#dbContentHeaderAppend">
    <span style="font-size: 16px">【{{ formData.config_name }}】</span>
  </Teleport>
  <BkLoading :loading="isDetailLoading">
    <SmartAction :offset-target="getSmartActionOffsetTarget">
      <BkForm
        ref="form"
        class="mysql-template-create-page mb-32"
        :model="formData">
        <DbCard :title="t('基本信息')">
          <BkFormItem
            :label="t('模块名称')"
            property="config_name"
            required>
            <BkInput
              v-model="formData.config_name"
              :maxlength="32"
              :placeholder="t('请输入模板名称')"
              show-word-limit
              style="width: 560px" />
          </BkFormItem>
        </DbCard>
        <DbCard
          class="mt-18"
          property="source_cluster_id"
          :title="t('模板配置')">
          <BkFormItem
            :label="t('源集群')"
            required>
            <SourceCluster
              ref="sourceClusterRef"
              v-model="formData.source_cluster_id" />
          </BkFormItem>
          <BkFormItem
            :label="t('克隆的规则')"
            required>
            <ConfigRule
              ref="configRuleRef"
              :cluster-id="formData.source_cluster_id"
              :data="formData.config_rules" />
          </BkFormItem>
          <BkFormItem :label="t('初始化权限规则')">
            <PermissionRule
              ref="permissionRuleRef"
              v-model="permissionRules"
              v-model:source-cluster-id="formData.source_cluster_id" />
          </BkFormItem>
        </DbCard>
      </BkForm>
      <template #action>
        <BkButton
          class="w-88"
          :disabled="!formDataChanged"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :disabled="!formDataChanged"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { create as createOpenarea, getDetail, update as updateOpenarea } from '@services/source/openarea';

  import { useBeforeClose } from '@hooks';

  import { TicketTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  import ConfigRule from './config-rule/Index.vue';
  import PermissionRule from './permission-rule/Index.vue';
  import SourceCluster from './source-cluster/Index.vue';

  type CreateOpenareaParams = ServiceParameters<typeof createOpenarea>;

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const handleBeforeClose = useBeforeClose();

  const isEditMode = route.name === 'MySQLOpenareaTemplateEdit';

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const formRef = useTemplateRef('form');

  const sourceClusterRef = ref<InstanceType<typeof SourceCluster>>();
  const configRuleRef = ref<InstanceType<typeof ConfigRule>>();
  const permissionRuleRef = ref<InstanceType<typeof PermissionRule>>();

  const isSubmitting = ref(false);
  const permissionRules = ref<number[]>([]);
  const formDataChanged = ref(false);

  const genDefaultValue = () => ({
    config_name: '',
    config_rules: [] as ServiceReturnType<typeof getDetail>['config_rules'],
    source_cluster_id: 0,
  });

  const formData = reactive(genDefaultValue());

  // 编辑态获取模版详情
  const { loading: isDetailLoading, run: fetchTemplateDetail } = useRequest(getDetail, {
    manual: true,
    async onSuccess(data) {
      formData.config_name = data.config_name;
      formData.source_cluster_id = data.source_cluster_id;
      formData.config_rules = data.config_rules;

      sourceClusterRef.value?.set({
        domain: data.source_cluster.immute_domain,
        type: data.cluster_type,
      });

      permissionRules.value = data.related_authorize;
    },
  });

  watch(
    formData,
    () => {
      window.changeConfirm = true;
      formDataChanged.value = true;
    },
    {
      deep: true,
    },
  );

  if (isEditMode) {
    fetchTemplateDetail({
      id: Number(route.params.id),
    });
  }

  const handleSubmit = async () => {
    if (isSubmitting.value) return;
    isSubmitting.value = true;

    try {
      const [configRule] = await Promise.all([configRuleRef.value?.getValue(), formRef.value?.validate()]);

      if (!configRule) {
        isSubmitting.value = false;
        return;
      }

      const params: { id: number } & CreateOpenareaParams = {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        id: isEditMode ? Number(route.params.id) : 0,
        ...formData,
        cluster_type: sourceClusterRef.value?.get().type,
        config_rules: configRule,
        related_authorize: permissionRules.value,
      };

      const handler = isEditMode ? updateOpenarea : createOpenarea;
      await handler(params);

      messageSuccess(isEditMode ? t('编辑成功') : t('新建成功'));
      window.changeConfirm = false;
      router.push({ name: TicketTypes.MYSQL_OPEN_AREA });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    Object.assign(formData, genDefaultValue());
    sourceClusterRef.value?.reset();
    permissionRuleRef.value?.reset();
    nextTick(() => {
      window.changeConfirm = false;
      formDataChanged.value = false;
    });
  };

  const handleCancel = async () => {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    router.push({
      name: 'MySQLOpenareaTemplate',
    });
  };

  defineExpose({
    routerBack() {
      router.push({
        name: 'MySQLOpenareaTemplate',
      });
    },
  });
</script>
<style lang="less">
  .mysql-template-create-page {
    .bk-form-label {
      font-size: 12px;
    }
  }
</style>
