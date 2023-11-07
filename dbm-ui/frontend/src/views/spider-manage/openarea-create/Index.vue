<template>
  <SmartAction
    class="spider-openarea-page"
    :offset-target="getSmartActionOffsetTarget">
    <BkForm class="mb-32">
      <DbCard :title="t('基本信息')">
        <BkFormItem
          :label="t('模块名称')"
          required>
          <BkInput
            :maxlength="32"
            :placeholder="t('请输入模板名称')"
            show-word-limit
            style="width: 560px" />
        </BkFormItem>
      </DbCard>
      <DbCard
        class="mt-18"
        :title="t('模板配置')">
        <BkFormItem
          :label="t('源集群')"
          required>
          <BkInput style="width: 560px" />
        </BkFormItem>
        <BkFormItem
          :label="t('克隆的规则')"
          required>
          <ConfigRule />
        </BkFormItem>
      </DbCard>
    </BkForm>
    <template #action>
      <BkButton
        class="w-88"
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
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import ConfigRule from './components/config-rule/Index.vue';

  const { t } = useI18n();

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const handleSubmit = () => {
    console.log('submit');
  };

  const handleReset = () => {
    console.log('reset');
  };
</script>
<style lang="less">
  .spider-openarea-page {
    display: block
  }
</style>
