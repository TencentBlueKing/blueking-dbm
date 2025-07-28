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
      <BkLoading
        class="mb-36"
        :loading="machinePropertyLoading">
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
            v-for="item in machinePropertyOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
        <DbForm
          ref="formRef"
          form-type="vertical"
          :model="formData">
          <div
            v-for="item in selectedOptions"
            :key="item"
            class="mb-16 setting-item">
            <DbIcon
              class="close-icon"
              type="close"
              @click.stop="() => handleDelete(item)" />
            <DbFormItem :label="settingMap[item].label">
              <Component
                :is="settingMap[item].content"
                ref="itemRef"
                v-model="formData[item as keyof UnwrapRef<typeof formData>]"
                :form-data="formData" />
            </DbFormItem>
          </div>
        </DbForm>
      </BkLoading>
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
        class="ml-8"
        :disabled="isSubmiting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { type Component, reactive, ref, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateResource } from '@services/source/dbresourceResource';
  import { getMachineProperty } from '@services/source/systemSettings';

  import { leaveConfirm } from '@utils';

  import City from './components/City.vue';
  import DeviceClass from './components/DeviceClass.vue';
  import Rack from './components/Rack.vue';
  import StorageDevice, { type IStorageDeviceItem } from './components/StorageDevice.vue';
  import SubZone from './components/SubZone.vue';

  interface Props {
    data: number[];
    isShow: boolean;
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'success'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const genDefaultData = () => ({
    city_meta: '' as string | number,
    device_class: '',
    rack_id: '',
    storage_device: [] as IStorageDeviceItem[],
    sub_zone_meta: '' as string | number,
  });

  const settingMap: Record<
    string,
    {
      content: Component;
      label: string;
      type: string;
    }
  > = {
    city_meta: {
      content: City,
      label: t('地域'),
      type: 'number',
    },
    device_class: {
      content: DeviceClass,
      label: t('机型'),
      type: 'string',
    },
    rack_id: {
      content: Rack,
      label: t('机架'),
      type: 'string',
    },
    storage_device: {
      content: StorageDevice,
      label: t('磁盘'),
      type: 'array',
    },
    sub_zone_meta: {
      content: SubZone,
      label: t('园区'),
      type: 'number',
    },
  };

  const formRef = useTemplateRef('formRef');
  const itemRef = useTemplateRef<
    {
      getValue: () => Record<string, any> | undefined;
    }[] &
      Component
  >('itemRef');

  const isSubmiting = ref(false);
  const selectedOptions = ref<string[]>([]);

  const formData = reactive(genDefaultData());

  const isSubmitDisabled = computed(
    () =>
      !Object.entries(formData).some(([formItemKey, formItemValue]) => {
        const type = settingMap[formItemKey].type;
        if (type === 'number') {
          return _.isNumber(formItemValue);
        }
        return !_.isEmpty(formItemValue);
      }),
  );

  const machinePropertyOptions = computed(() =>
    Object.entries(machinePropertyData.value || {}).reduce<
      {
        label: string;
        value: string;
      }[]
    >((prev, [key, isShow]) => {
      if (isShow) {
        return prev.concat({
          label: settingMap[key].label,
          value: key,
        });
      }
      return prev;
    }, []),
  );

  const { data: machinePropertyData, loading: machinePropertyLoading } = useRequest(getMachineProperty);

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
    formRef
      .value!.validate()
      .then(() => {
        const params = itemRef.value!.reduce<Record<string, any>>((prev, item) => {
          const value = item.getValue();
          if (value) {
            return Object.assign(prev, value);
          }
          return prev;
        }, {});

        return updateResource({
          bk_host_ids: props.data,
          ...params,
        }).then(() => {
          window.changeConfirm = false;
          emits('success');
          handleCancel();
        });
      })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleDelete = (key: string) => {
    selectedOptions.value = selectedOptions.value.filter((item) => item !== key);

    const type = settingMap[key].type;
    if (type === 'string' || type === 'number') {
      Object.assign(formData, { [key]: '' });
    } else if (type === 'array') {
      Object.assign(formData, { [key]: [] });
    }
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
      padding: 6px;

      .close-icon {
        position: absolute;
        top: 10px;
        right: 10px;
        visibility: hidden;
      }

      &:hover {
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
