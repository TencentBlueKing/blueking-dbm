<template>
  <DbSideslider
    :is-show="isShow"
    :width="800"
    @update:is-show="handleCancel">
    <template #header>
      <span>{{ t('主机属性') }}</span>
      <span style="margin-left: 12px; font-size: 12px; color: #63656e">
        <I18nT keypath="已选:n台主机">
          <span class="number">{{ selected.length }}</span>
        </I18nT>
      </span>
    </template>
    <div class="resource-pool-batch-setting">
      <BkLoading
        class="mb-36"
        :loading="machinePropertyLoading">
        <DbSelect
          v-model="selectedOptions"
          class="mb-16 setting-item-selector"
          multiple
          @change="handleOptionChange">
          <template #trigger>
            <BkButton class="trigger-button">
              <DbIcon
                class="mr-12"
                type="add" />
              {{ t('添加属性') }}
            </BkButton>
          </template>
          <DbOption
            v-for="item in machinePropertyOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value" />
        </DbSelect>
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
              type="delete"
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

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { updateResource } from '@services/source/dbresourceResource';
  import { getMachineProperty } from '@services/source/systemSettings';

  import { useSystemEnviron } from '@stores';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';
  import { MachineEvents } from '@common/const/machineEvents';

  import { leaveConfirm } from '@utils';

  import City from './components/City.vue';
  import DeviceClassItem from './components/DeviceClass.vue';
  import Rack from './components/Rack.vue';
  import StorageDevice, { createRowData } from './components/StorageDevice.vue';
  import SubZone from './components/SubZone.vue';

  interface Props {
    isShow: boolean;
    selected: DbResourceModel[];
  }

  interface Emits {
    (e: 'update:isShow', value: boolean): void;
    (e: 'success'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();
  const systemEnvironStore = useSystemEnviron();

  const isBusiness = route.name === 'BizResourcePool';
  const defaultBizId = systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ;

  const genDefaultData = () => ({
    city_meta: '' as string | number,
    device_class: '',
    rack_id: '',
    storage_device: [createRowData()],
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
      content: DeviceClassItem,
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
      label: t('数据盘'),
      type: 'array',
    },
    sub_zone_meta: {
      content: SubZone,
      label: t('园区'),
      type: 'number',
    },
  };

  const formRef = useTemplateRef('formRef');
  const itemRef = ref<
    InstanceType<typeof City | typeof DeviceClassItem | typeof Rack | typeof StorageDevice | typeof SubZone>[]
  >([]);

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

  const handleOptionChange = () => {
    window.changeConfirm = true;
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    const valuePromiseList = itemRef.value!.map((item) => Promise.resolve(item.getValue()));
    Promise.all(valuePromiseList)
      .then((result) => {
        const params: Pick<
          ServiceParameters<typeof updateResource>,
          'city_meta' | 'device_class' | 'rack_id' | 'storage_device' | 'sub_zone_meta'
        > = result.reduce<Record<string, any>>((prev, resultItem) => {
          return Object.assign(prev, resultItem);
        }, {});

        const cityAfter = params.city_meta?.city || '';
        const subZoneAfter = params.sub_zone_meta?.sub_zone || '';
        const rackIdAfter = params.rack_id || '';
        const deviceClassAfter = params.device_class || '';
        const storageDeviceAfter = params.storage_device
          ? `（${Object.entries(params.storage_device)
              .map(([key, item]) => `${key}:${item.size}G:${deviceClassDisplayMap[item.disk_type as DeviceClass]}`)
              .join(';')}）`
          : '';

        const remarkList = props.selected.map((item) => {
          const cityBefore = item.city;
          const subZoneBefore = item.sub_zone;
          const rackIdBefore = item.rack_id;
          const deviceClassBefore = item.device_class;
          const storageDeviceBefore = _.isEmpty(item.storage_device)
            ? ''
            : `（${Object.entries(item.storage_device)
                .map(([key, item]) => `${key}:${item.size}G:${deviceClassDisplayMap[item.disk_type as DeviceClass]}`)
                .join(';')}）`;

          const remarkItem = {} as NonNullable<ServiceParameters<typeof updateResource>['remark']>[number];
          if (cityAfter) {
            Object.assign(remarkItem, { city: { after_value: cityAfter, before_value: cityBefore } });
          }
          if (subZoneAfter) {
            Object.assign(remarkItem, { sub_zone: { after_value: subZoneAfter, before_value: subZoneBefore } });
          }
          if (rackIdAfter) {
            Object.assign(remarkItem, { rack_id: { after_value: rackIdAfter, before_value: rackIdBefore } });
          }
          if (deviceClassAfter) {
            Object.assign(remarkItem, {
              device_class: { after_value: deviceClassAfter, before_value: deviceClassBefore },
            });
          }
          if (storageDeviceAfter) {
            Object.assign(remarkItem, {
              storage_device: { after_value: storageDeviceAfter, before_value: storageDeviceBefore },
            });
          }
          return remarkItem;
        });

        return updateResource({
          bk_biz_id: isBusiness ? window.PROJECT_CONFIG.BIZ_ID : defaultBizId,
          bk_host_ids: props.selected.map((item) => item.bk_host_id),
          host_id_ip_map: props.selected.reduce<Record<string, string>>((prev, item) => {
            return Object.assign(prev, { [item.bk_host_id]: item.ip });
          }, {}),
          remark: remarkList,
          update_type: MachineEvents.HOST_ATTRIBUTE,
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
    padding: 16px 24px 0;

    .com-input {
      display: flex;

      .dbm-select {
        flex: 1;
      }
    }

    .setting-item-selector {
      width: 352px;

      .trigger-button {
        font-size: 16px;
      }
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
