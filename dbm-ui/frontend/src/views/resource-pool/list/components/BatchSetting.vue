<template>
  <BkDialog
    :is-show="isShow"
    :title="t('设置业务专用')">
    <div class="mb-36">
      <div class="mb-16">
        <I18nT keypath="已选:n台主机">
          <span class="number">{{ data.length }}</span>
        </I18nT>
      </div>
      <DbForm
        form-type="vertical"
        :model="formData">
        <DbFormItem
          :label="t('专用业务')"
          property="for_bizs">
          <BkSelect
            v-model="formData.for_bizs"
            :loading="isBizListLoading"
            multiple>
            <BkOption
              v-for="bizItem in bizList"
              :key="bizItem.bk_biz_id"
              :label="bizItem.display_name"
              :value="bizItem.bk_biz_id" />
          </BkSelect>
        </DbFormItem>
        <DbFormItem
          :label="t('专用 DB')"
          property="resource_types">
          <BkSelect
            v-model="formData.resource_types"
            :loading="isDbTypeListLoading"
            multiple>
            <BkOption
              v-for="item in dbTypeList"
              :key="item.id"
              :label="item.name"
              :value="item.id" />
          </BkSelect>
        </DbFormItem>
      </DbForm>
    </div>
    <template #footer>
      <BkButton
        :loading="isSubmiting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import {
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/common';
  import { updateResource } from '@services/dbResource';
  import { fetchDbTypeList } from '@services/infras';

  interface Props {
    data: number[],
    isShow: boolean,
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void,
    (e: 'change'): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const genDefaultData = () => ({
    for_bizs: [],
    resource_types: [],
  });

  const isSubmiting = ref(false);
  const formData = reactive(genDefaultData());

  const {
    data: bizList,
    loading: isBizListLoading,
  } = useRequest(getBizs);

  const {
    data: dbTypeList,
    loading: isDbTypeListLoading,
  } = useRequest(fetchDbTypeList);

  const handleSubmit = () => {
    isSubmiting.value = true;
    updateResource({
      bk_host_ids: props.data.map(item => ~~item),
      for_bizs: formData.for_bizs,
      resource_types: formData.resource_types,
    }).then(() => {
      emits('change');
      handleCancel();
    })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleCancel = () => {
    emits('update:isShow', false);
    Object.assign(formData, genDefaultData());
  };
</script>

