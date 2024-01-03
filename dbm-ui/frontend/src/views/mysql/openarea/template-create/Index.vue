<template>
  <BkLoading :loading="isDetailLoading">
    <SmartAction
      class="mysql-openarea-page"
      :offset-target="getSmartActionOffsetTarget">
      <BkForm
        ref="formRef"
        class="mb-32"
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
            <BkSelect
              v-model="formData.source_cluster_id"
              filterable
              :input-search="false"
              style="width: 560px">
              <BkOption
                v-for="item in clusterList"
                :id="item.id"
                :key="item.id"
                :name="`${item.name} (${item.id})`" />
            </BkSelect>
          </BkFormItem>
          <BkFormItem
            :label="t('克隆的规则')"
            required>
            <ConfigRule
              ref="configRuleRef"
              :cluster-id="formData.source_cluster_id"
              :data="formData.config_rules" />
          </BkFormItem>
        </DbCard>
      </BkForm>
      <template #action>
        <BkButton
          class="w-88"
          :loading="isSubmiting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="ts">
  import { Form } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import { queryAllTypeCluster } from '@services/dbbase';
  import {
    getDetail,
    update as updateOpenarea,
  } from '@services/openarea';

  import { useGlobalBizs } from '@stores';

  import { messageSuccess } from '@utils';

  import ConfigRule from './components/config-rule/Index.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();

  const isEditMode = route.name === 'mysqlOpenareaTemplateEdit';

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const genDefaultValue = () => ({
    config_name: '',
    source_cluster_id: 0,
    config_rules: [] as ServiceReturnType<typeof getDetail>['config_rules'],
  });

  const configRuleRef = ref<InstanceType<typeof ConfigRule>>();
  const formRef = ref<InstanceType<typeof Form>>();
  const isSubmiting = ref(false);

  const formData = reactive(genDefaultValue());

  const {
    data: clusterList,
  } = useRequest(queryAllTypeCluster, {
    defaultParams: [
      {
        bk_biz_id: currentBizId,
        cluster_types: 'tendbha',
        phase: 'online',
      },
    ],
  });

  // 编辑态获取模版详情
  const {
    loading: isDetailLoading,
    run: fetchTemplateDetail,
  } = useRequest(getDetail, {
    manual: true,
    onSuccess(data) {
      formData.config_name = data.config_name;
      formData.source_cluster_id = data.source_cluster_id;
      formData.config_rules = data.config_rules;
    },
  });

  if (isEditMode) {
    fetchTemplateDetail({
      id: Number(route.params.id),
    });
  }

  const handleSubmit = () => {
    isSubmiting.value = true;
    Promise.all([
      (configRuleRef.value as InstanceType<typeof ConfigRule>).getValue(),
      (formRef.value as InstanceType<typeof Form>).validate(),
    ]).then(([configRule]) => updateOpenarea({
      id: Number(route.params.id),
      bk_biz_id: currentBizId,
      ...formData,
      config_rules: configRule,
      cluster_type: 'tendbha',
    }).then(() => {
      messageSuccess(t('编辑成功'));
      window.changeConfirm = false;
      router.push({
        name: 'mysqlOpenareaTemplate',
      });
    }))
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleReset = () => {
    Object.assign(formData, genDefaultValue());
  };
</script>
