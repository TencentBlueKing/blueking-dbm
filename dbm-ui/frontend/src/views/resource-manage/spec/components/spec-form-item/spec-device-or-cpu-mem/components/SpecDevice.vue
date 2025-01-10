<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="spec-device spec-form-item">
    <div class="spec-form-item-content">
      <BkFormItem
        property="device_class"
        required
        :rules="rules"
        style="width: 100%">
        <BkSelect
          :allow-empty-values="['']"
          class="device-class-select"
          :clearable="false"
          filterable
          :input-search="false"
          :loading="isLoading"
          :model-value="modelValue"
          multiple
          :popover-min-width="330"
          :remote-method="remoteMethod"
          :scroll-height="384"
          :scroll-loading="scrollLoading"
          selected-style="checkbox"
          @change="handleSelectChange"
          @scroll-end="handleScrollEnd">
          <template #trigger>
            <BkButton
              style="font-size: 14px"
              text
              theme="primary">
              <DbIcon
                style="margin-right: 5px"
                type="plus-fill" />
              {{ t('添加机型') }}
            </BkButton>
          </template>
          <BkOption
            v-for="item in deviceClassList"
            :key="item.value"
            :value="item.value">
            <div class="device-list-item">
              <span>
                {{ item.label }}
              </span>
              <span style="color: #c4c6cc">{{ `${item.cpu}${t('核')}${item.mem}G` }}</span>
            </div>
          </BkOption>
        </BkSelect>
        <!-- <div
          v-bk-tooltips="{
            content: t('不支持修改'),
            disabled: !isEdit,
          }"> -->
        <BkTag
          v-for="(item, index) in modelValue"
          :key="`${item}-${index}`"
          closable
          style="background-color: #fff"
          @close="() => handleTagClose(index)">
          {{
            deviceListMap[item]?.cpu
              ? `${item}（${deviceListMap[item]?.cpu}${t('核')}${deviceListMap[item]?.mem}G）`
              : `${item}`
          }}
        </BkTag>
        <!-- </div> -->
      </BkFormItem>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  export type DeviceClassCpuMemType = typeof selectedCpuMem;

  interface Props {
    isEdit: boolean;
    cpu: {
      min: number | string;
      max: number | string;
    };
    mem: {
      min: number | string;
      max: number | string;
    };
  }

  interface Exposes {
    getDeviceClassCpuMem: () => DeviceClassCpuMemType;
  }

  interface DeviceClassListItem {
    cpu: number;
    mem: number;
    label: string;
    value: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
  });

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const deviceClassList = ref<DeviceClassListItem[]>([]);
  const scrollLoading = ref(false);
  const deviceListMap = ref<
    Record<
      string,
      {
        cpu: number;
        mem: number;
      }
    >
  >({});

  const searchParams = {
    offset: 0,
    limit: 12,
    device_type: '',
  };

  const selectedCpuMem = {
    cpu: {
      min: Number.MAX_SAFE_INTEGER,
      max: -Number.MAX_SAFE_INTEGER,
    },
    mem: {
      min: Number.MAX_SAFE_INTEGER,
      max: -Number.MAX_SAFE_INTEGER,
    },
  };

  const rules = [
    {
      required: true,
      validator: (value: string[]) => value.length > 0,
      message: t('请选择xx', [t('机型')]),
    },
  ];

  let isAppend = false;
  let oldData: string[] = [];

  useRequest(fetchDeviceClass, {
    defaultParams: [
      {
        offset: 0,
        limit: -1,
      },
    ],
    onSuccess(data) {
      data.results.forEach((item) => {
        deviceListMap.value[item.device_type] = {
          cpu: item.cpu,
          mem: item.mem,
        };
      });
    },
  });

  const { loading: isLoading, run: getDeviceClassList } = useRequest(fetchDeviceClass, {
    manual: true,
    onSuccess(data) {
      scrollLoading.value = false;
      const deviceList: DeviceClassListItem[] = [];
      data.results.forEach((item) => {
        deviceList.push({
          label: item.device_type,
          cpu: item.cpu,
          mem: item.mem,
          value: item.device_type,
        });
      });
      if (isAppend) {
        deviceClassList.value.push(...deviceList);
        return;
      }

      deviceClassList.value = deviceList;
    },
  });

  watch(
    () => [props.cpu, props.mem],
    () => {
      if (typeof props.cpu.max !== 'string') {
        selectedCpuMem.cpu = props.cpu as DeviceClassCpuMemType['cpu'];
        selectedCpuMem.mem = props.mem as DeviceClassCpuMemType['mem'];
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => modelValue.value,
    () => {
      if (modelValue.value.length > 0) {
        oldData = _.cloneDeep(modelValue.value);
      }

      getDeviceClassList(searchParams);
    },
    { immediate: true },
  );

  const handleTagClose = (index: number) => {
    if (props.isEdit) {
      const value = modelValue.value[index];
      if (oldData.includes(value)) {
        return;
      }
    }
    modelValue.value.splice(index, 1);
  };

  const handleScrollEnd = () => {
    scrollLoading.value = true;
    isAppend = true;
    searchParams.offset += searchParams.limit;
    getDeviceClassList(searchParams);
  };

  const remoteMethod = (value: string) => {
    isAppend = false;
    searchParams.device_type = value;
    searchParams.offset = 0;
    getDeviceClassList(searchParams);
  };

  const handleSelectChange = (list: string[]) => {
    list.forEach((item) => {
      const itemInfo = deviceListMap.value[item];
      selectedCpuMem.cpu.min = itemInfo.cpu < selectedCpuMem.cpu.min ? itemInfo.cpu : selectedCpuMem.cpu.min;
      selectedCpuMem.cpu.max = itemInfo.cpu > selectedCpuMem.cpu.max ? itemInfo.cpu : selectedCpuMem.cpu.max;
      selectedCpuMem.mem.min = itemInfo.mem < selectedCpuMem.mem.min ? itemInfo.mem : selectedCpuMem.mem.min;
      selectedCpuMem.mem.max = itemInfo.mem > selectedCpuMem.mem.max ? itemInfo.mem : selectedCpuMem.mem.max;
    });
    modelValue.value = list;
  };

  defineExpose<Exposes>({
    getDeviceClassCpuMem() {
      return selectedCpuMem;
    },
  });
</script>

<style lang="less" scoped>
  @import '../../specFormItem.less';

  .spec-device {
    padding: 0 !important;
  }

  .device-class-select {
    max-width: 330px;
  }
</style>
<style lang="less">
  .bk-select-option {
    padding-right: 12px !important;
  }

  .device-list-item {
    display: flex;
    width: 100%;
    justify-content: space-between;
  }
</style>
