<template>
  <DbSideslider
    :is-show="isShow"
    :width="800"
    @update:is-show="handleCancel">
    <template #header>
      <span>{{ t('设置业务专用') }}</span>
      <span style=" margin-left: 12px;font-size: 12px; color: #63656E;">
        <I18nT keypath="已选:n台主机">
          <span class="number">{{ data.length }}</span>
        </I18nT>
      </span>
    </template>
    <div class="resource-pool-batch-setting">
      <div class="mb-36">
        <DbForm
          ref="formRef"
          form-type="vertical"
          :model="formData">
          <DbFormItem
            :label="t('专用业务')"
            property="for_bizs">
            <div class="com-input">
              <BkSelect
                v-model="formData.for_bizs"
                :disabled="formData.set_empty_biz"
                :loading="isBizListLoading"
                multiple
                multiple-mode="tag">
                <BkOption
                  v-for="bizItem in bizList"
                  :key="bizItem.bk_biz_id"
                  :label="bizItem.display_name"
                  :value="bizItem.bk_biz_id" />
              </BkSelect>
              <BkCheckbox
                v-model="formData.set_empty_biz"
                class="ml-12"
                @change="handleEmptyBizChange">
                {{ t('无限制') }}
              </BkCheckbox>
            </div>
          </DbFormItem>
          <DbFormItem
            :label="t('专用 DB')"
            property="resource_types">
            <div class="com-input">
              <BkSelect
                v-model="formData.resource_types"
                :disabled="formData.set_empty_resource_type"
                :loading="isDbTypeListLoading"
                multiple
                multiple-mode="tag">
                <BkOption
                  v-for="item in dbTypeList"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id" />
              </BkSelect>
              <BkCheckbox
                v-model="formData.set_empty_resource_type"
                class="ml-12"
                @change="handleEmptyResourceTypeChange">
                {{ t('无限制') }}
              </BkCheckbox>
            </div>
          </DbFormItem>
          <DbFormItem :label="t('磁盘')">
            <ResourceSpecStorage
              v-model="formData.storage_spec" />
          </DbFormItem>
        </DbForm>
      </div>
    </div>
    <template #footer>
      <BkButton
        :disabled="isSubmitDisabled"
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
  </DbSideslider>
</template>
<script setup lang="ts">
  import {
    computed,
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/common';
  import { updateResource } from '@services/dbResource';
  import { fetchDbTypeList } from '@services/infras';

  import { leaveConfirm } from '@utils';

  import ResourceSpecStorage, {
    type IStorageSpecItem,
  } from './components/ResourceSpecStorage.vue';

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
    storage_spec: [] as IStorageSpecItem[],
    set_empty_biz: false,
    set_empty_resource_type: false,
  });

  const formRef = ref();
  const isSubmiting = ref(false);
  const formData = reactive(genDefaultData());

  const isSubmitDisabled = computed(() => !(
    formData.for_bizs.length > 0
    || formData.resource_types.length > 0
    || formData.storage_spec.length > 0
    || formData.set_empty_biz
    || formData.set_empty_resource_type));

  const {
    data: bizList,
    loading: isBizListLoading,
  } = useRequest(getBizs);

  const {
    data: dbTypeList,
    loading: isDbTypeListLoading,
  } = useRequest(fetchDbTypeList);

  const handleEmptyBizChange = () => {
    formData.for_bizs = [];
  };

  const handleEmptyResourceTypeChange = () => {
    formData.resource_types = [];
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    formRef.value.validate()
      .then(() => {
        const storageDevice = formData.storage_spec.reduce((result, item) => ({
          ...result,
          [item.mount_point]: {
            size: item.size,
            disk_type: item.type,
          },
        }), {} as Record<string, {size: number, disk_type: string}>);
        return updateResource({
          bk_host_ids: props.data.map(item => ~~item),
          for_bizs: formData.set_empty_biz ? [] : formData.for_bizs,
          resource_types: formData.set_empty_resource_type ? [] : formData.resource_types,
          set_empty_biz: formData.set_empty_biz,
          set_empty_resource_type: formData.set_empty_resource_type,
          storage_device: storageDevice,
        }).then(() => {
          window.changeConfirm = false;
          emits('change');
          handleCancel();
        });
      })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleCancel = () => {
    leaveConfirm()
      .then(() => {
        emits('update:isShow', false);
        Object.assign(formData, genDefaultData());
        // 重置数据时会触发form的编辑状态检测，需要重置检测状态
        setTimeout(() => {
          window.changeConfirm = false;
        }, 100);
      });
  };
</script>
<style lang="less">
  .resource-pool-batch-setting {
    padding: 20px 40px 0;

    .com-input {
      display: flex;

      .bk-select {
        flex: 1
      }
    }
  }
</style>
