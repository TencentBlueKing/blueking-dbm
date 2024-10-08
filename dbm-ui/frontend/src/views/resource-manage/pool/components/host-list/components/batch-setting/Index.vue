<template>
  <DbSideslider
    :is-show="isShow"
    :width="800"
    @update:is-show="handleCancel">
    <template #header>
      <span>{{ t('设置主机属性') }}</span>
      <span style="margin-left: 12px; font-size: 12px; color: #63656e">
        <I18nT keypath="已选:n台主机">
          <span class="number">{{ data.length }}</span>
        </I18nT>
      </span>
    </template>
    <div class="resource-pool-batch-setting">
      <div class="mb-36">
        <BkSelect
          v-model="selectedOptions"
          class="mb-16 setting-item-selector"
          multiple>
          <template #trigger>
            <BkButton
              text
              theme="primary">
              <DbIcon type="plus-circle" /> {{ t('添加属性') }}
            </BkButton>
          </template>
          <BkOption
            v-for="item in SETTING_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
        <DbForm
          ref="formRef"
          form-type="vertical"
          :model="formData">
          <div
            v-if="selectedOptions.includes('storage_spec')"
            class="mb-16 setting-item">
            <DbIcon
              class="close-icon"
              type="close"
              @click.stop="() => handleDelete('storage_spec')" />
            <DbFormItem :label="t('磁盘')">
              <ResourceSpecStorage v-model="formData.storage_spec" />
            </DbFormItem>
          </div>
          <div
            v-if="selectedOptions.includes('rack_id')"
            class="mb-16 setting-item">
            <DbIcon
              class="close-icon"
              type="close"
              @click.stop="() => handleDelete('rack_id')" />
            <DbFormItem :label="t('机架')">
              <BkInput v-model="formData.rack_id" />
            </DbFormItem>
          </div>
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
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizs } from '@services/source/cmdb';
  import { updateResource } from '@services/source/dbresourceResource';
  import { fetchDbTypeList } from '@services/source/infras';

  import { leaveConfirm } from '@utils';

  import ResourceSpecStorage, { type IStorageSpecItem } from './components/ResourceSpecStorage.vue';

  import type { BizItem } from '@/services/types';

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
    rack_id: '',
    storage_spec: [] as IStorageSpecItem[],
  });

  const formRef = ref();
  const isSubmiting = ref(false);
  const bizList = shallowRef<ServiceReturnType<typeof getBizs>>([]);
  const dbTypeList = shallowRef<ServiceReturnType<typeof fetchDbTypeList>>([]);

  const selectedOptions = ref<string[]>([]);

  const formData = reactive(genDefaultData());

  const isSubmitDisabled = computed(() => !(formData.storage_spec.length > 0 || formData.rack_id));

  const SETTING_OPTIONS = [
    {
      label: t('磁盘'),
      value: 'storage_spec',
    },
    {
      label: t('机架'),
      value: 'rack_id',
    },
  ];

  useRequest(getBizs, {
    onSuccess(data) {
      bizList.value = [
        {
          bk_biz_id: 0,
          display_name: t('公共资源池'),
        } as BizItem,
        ...data,
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

  watch(
    () => props.isShow,
    () => {
      if (props.isShow) {
        selectedOptions.value = [];
      }
    },
  );

  const handleSubmit = () => {
    isSubmiting.value = true;
    formRef.value
      .validate()
      .then(() => {
        const storageDevice = formData.storage_spec.reduce<Record<string, { size: number; disk_type: string }>>(
          (result, item) => ({
            ...result,
            [item.mount_point]: {
              size: item.size,
              disk_type: item.type,
            },
          }),
          {},
        );
        const params = {
          bk_host_ids: props.data.map((item) => ~~item),
          rack_id: formData.rack_id,
          storage_device: storageDevice,
        };

        return updateResource(params).then(() => {
          window.changeConfirm = false;
          emits('change');
          handleCancel();
        });
      })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleDelete = (value: 'storage_spec' | 'rack_id') => {
    selectedOptions.value = selectedOptions.value.filter((item) => item !== value);
    formData[value] = undefined;
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

    .setting-item-selector {
      width: 352px;
    }

    .setting-item {
      position: relative;

      .close-icon {
        position: absolute;
        top: 10px;
        right: 10px;
        visibility: hidden;
      }

      &:hover {
        padding: 6px;
        background-color: #f0f1f5;

        .close-icon {
          z-index: 99;
          cursor: pointer;
          visibility: visible;
        }
      }
    }
  }
</style>
