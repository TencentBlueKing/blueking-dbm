<template>
  <DbSideslider
    :is-show="isShow"
    :width="800"
    @update:is-show="handleCancel">
    <template #header>
      <span>{{ t('设置业务专用') }}</span>
      <span style="margin-left: 12px; font-size: 12px; color: #63656e">
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
            :label="t('所属业务')"
            property="for_biz">
            <div class="com-input">
              <BkSelect
                v-model="formData.for_biz"
                filterable>
                <BkOption
                  v-for="bizItem in bizList"
                  :key="bizItem.bk_biz_id"
                  :label="bizItem.display_name"
                  :value="bizItem.bk_biz_id" />
              </BkSelect>
            </div>
          </DbFormItem>
          <DbFormItem
            :label="t('所属DB类型')"
            property="resource_type">
            <div class="com-input">
              <BkSelect
                v-model="formData.resource_type"
                filterable>
                <BkOption
                  v-for="item in dbTypeList"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id" />
              </BkSelect>
            </div>
          </DbFormItem>
          <DbFormItem :label="t('磁盘')">
            <ResourceSpecStorage v-model="formData.storage_spec" />
          </DbFormItem>
          <DbFormItem :label="t('机架')">
            <BkInput v-model="formData.rack_id" />
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
  import { computed, reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/source/cmdb';
  import { updateResource } from '@services/source/dbresourceResource';
  import { fetchDbTypeList } from '@services/source/infras';

  import { leaveConfirm } from '@utils';

  import ResourceSpecStorage, { type IStorageSpecItem } from './components/ResourceSpecStorage.vue';

  interface Props {
    data: number[];
    isShow: boolean;
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'change'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const genDefaultData = () => ({
    for_biz: '',
    rack_id: '',
    resource_type: '',
    storage_spec: [] as IStorageSpecItem[],
  });

  const formRef = ref();
  const isSubmiting = ref(false);
  const bizList = shallowRef<
    {
      bk_biz_id: string;
      display_name: string;
    }[]
  >([]);
  const dbTypeList = shallowRef<
    {
      id: string;
      name: string;
    }[]
  >([]);
  const formData = reactive(genDefaultData());

  const isSubmitDisabled = computed(
    () => !(formData.for_biz || formData.resource_type || formData.storage_spec.length > 0),
  );

  useRequest(getBizs, {
    onSuccess(data) {
      bizList.value = [
        { bk_biz_id: '0', display_name: t('公共资源池') },
        ...data.map((item) => ({
          bk_biz_id: `${item.bk_biz_id}`,
          display_name: item.display_name,
        })),
      ];
    },
  });

  useRequest(fetchDbTypeList, {
    onSuccess(data) {
      const cloneData = data;
      cloneData.unshift({
        id: 'PUBLIC',
        name: t('通用'),
      });
      dbTypeList.value = cloneData;
    },
  });

  const handleSubmit = () => {
    isSubmiting.value = true;
    formRef.value
      .validate()
      .then(() => {
        const storageDevice = formData.storage_spec.reduce(
          (result, item) => ({
            ...result,
            [item.mount_point]: {
              size: item.size,
              disk_type: item.type,
            },
          }),
          {} as Record<string, { size: number; disk_type: string }>,
        );
        return updateResource({
          bk_host_ids: props.data.map((item) => ~~item),
          for_biz: Number(formData.for_biz),
          rack_id: formData.rack_id,
          resource_type: formData.resource_type,
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
    leaveConfirm().then(() => {
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
        flex: 1;
      }
    }
  }
</style>
