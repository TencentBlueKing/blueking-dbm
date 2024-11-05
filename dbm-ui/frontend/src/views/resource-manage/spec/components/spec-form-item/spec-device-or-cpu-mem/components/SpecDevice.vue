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
          :disabled="isEdit"
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
              :disabled="isEdit"
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
            key="all"
            :label="t('无限制')"
            value="-1" />
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
        <div
          v-bk-tooltips="{
            content: t('不支持修改'),
            disabled: !isEdit,
          }">
          <BkTag
            v-for="(item, index) in modelValue"
            :key="`${item}-${index}`"
            closable
            style="background-color: #fff"
            @close="() => handleTagClose(index)">
            {{
              item === '-1'
                ? t('无限制')
                : deviceListMap[item]?.cpu
                  ? `${item}（${deviceListMap[item]?.cpu}${t('核')}${deviceListMap[item]?.mem}G）`
                  : `${item}`
            }}
          </BkTag>
        </div>
      </BkFormItem>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  interface Props {
    isEdit: boolean;
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

  const searchParams = {
    offset: 0,
    limit: 12,
    name: '',
  };

  const deviceListMap: Record<
    string,
    {
      cpu: number;
      mem: number;
    }
  > = {};

  const rules = [
    {
      required: true,
      validator: (value: string[]) => value.length > 0,
      message: t('请选择xx', [t('机型')]),
    },
  ];

  let isAppend = false;

  const { loading: isLoading, run: getDeviceClassList } = useRequest(fetchDeviceClass, {
    manual: true,
    onSuccess(data) {
      scrollLoading.value = false;
      const deviceList: DeviceClassListItem[] = [];
      data.results.forEach((item) => {
        deviceListMap[item.device_type] = {
          cpu: item.cpu,
          mem: item.mem,
        };

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
    () => modelValue.value,
    () => {
      if (modelValue.value.length > 0 && modelValue.value[0] !== '-1') {
        // 批量查询已选中的机型
        searchParams.name = modelValue.value.join(',');
        getDeviceClassList(searchParams);
        searchParams.name = '';
        return;
      }

      getDeviceClassList(searchParams);
    },
    { immediate: true },
  );

  const handleTagClose = (index: number) => {
    if (props.isEdit) {
      return;
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
    searchParams.name = value;
    searchParams.offset = 0;
    getDeviceClassList(searchParams);
  };

  const handleSelectChange = (list: string[]) => {
    if (list.length > 1) {
      if (list[0] === '-1') {
        // 先选的无限制，后续加选要去除无限制
        modelValue.value = list.slice(1);
        return;
      }

      if (list[list.length - 1] === '-1') {
        // 最后选的无限制，前面选过的都要去除
        modelValue.value = ['-1'];
        return;
      }
    }

    modelValue.value = list;
  };
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
