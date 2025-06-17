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
  <div class="resource-spec-storage-box">
    <DbOriginalTable
      :border="['row', 'col', 'outer']"
      class="custom-edit-table"
      :columns="columns"
      :data="modelValue">
      <template #empty>
        <div
          class="create-row"
          @click="handleCreate">
          <DbIcon type="add" />
        </div>
      </template>
    </DbOriginalTable>
  </div>
</template>
<script lang="tsx">
  export interface IStorageDeviceItem {
    mount_point: string;
    size: number;
    type: string;
  }
</script>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { updateResource } from '@services/source/dbresourceResource';
  import { searchDeviceClass } from '@services/source/ipchooser';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

  type StorageDevice = NonNullable<ServiceParameters<typeof updateResource>['storage_device']>;

  interface TableColumnData {
    data: IStorageDeviceItem;
    index: number;
  }

  interface Expose {
    getValue: () =>
      | {
          storage_device: StorageDevice;
        }
      | undefined;
  }

  const modelValue = defineModel<IStorageDeviceItem[]>({
    required: true,
  });

  const { t } = useI18n();

  const deviceClass = ref<{ label: string; value: string }[]>([]);
  const isLoadDeviceClass = ref(true);

  const mountPointRules = (data: IStorageDeviceItem) => {
    // 非必填
    if (!data.mount_point && !data.size && !data.type) {
      return [];
    }

    return [
      {
        message: t('输入需符合正则_regx', { regx: '/data(\\d)*/' }),
        trigger: 'blur',
        validator: (value: string) => /data(\d)*/.test(value),
      },
      {
        message: () => t('挂载点name重复', { name: data.mount_point }),
        trigger: 'blur',
        validator: (value: string) => modelValue.value.filter((item) => item.mount_point === value).length < 2,
      },
    ];
  };
  const sizeRules = (data: IStorageDeviceItem) => {
    // 非必填且其他输入框没有输入
    if (!data.mount_point && !data.type) {
      return [];
    }

    return [
      {
        message: t('必填项'),
        required: true,
        trigger: 'blur',
        validator: (value: string) => !!value,
      },
    ];
  };
  const typeRules = (data: IStorageDeviceItem) => {
    // 非必填且其他输入框没有输入
    if (!data.mount_point && !data.size) {
      return [];
    }

    return [
      {
        message: t('必填项'),
        required: true,
        trigger: 'change',
        validator: (value: string) => !!value,
      },
    ];
  };
  const columns = [
    {
      field: 'mount_point',
      label: t('挂载点'),
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          error-display-type='tooltips'
          property={`storage_device.${index}.mount_point`}
          rules={mountPointRules(data)}>
          <bk-input
            v-model={data.mount_point}
            class='large-size'
            placeholder='/data123'
          />
        </bk-form-item>
      ),
    },
    {
      field: 'size',
      label: t('磁盘容量G'),
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          error-display-type='tooltips'
          property={`storage_device.${index}.size`}
          rules={sizeRules(data)}>
          <bk-input
            class='large-size'
            min={10}
            modelValue={data.size || undefined}
            show-control={false}
            type='number'
            onChange={(value: string) => (data.size = Number(value))} // eslint-disable-line no-param-reassign
          />
        </bk-form-item>
      ),
    },
    {
      field: 'type',
      label: t('磁盘类型'),
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          error-display-type='tooltips'
          property={`storage_device.${index}.type`}
          rules={typeRules(data)}>
          <bk-select
            v-model={data.type}
            class='large-size'
            clearable={false}
            loading={isLoadDeviceClass.value}>
            {deviceClass.value.map((item) => (
              <bk-option
                label={item.label}
                value={item.value}
              />
            ))}
          </bk-select>
        </bk-form-item>
      ),
    },
    {
      field: '',
      label: t('操作'),
      render: ({ index }: TableColumnData) => (
        <div class='opertaions'>
          <bk-button
            text
            onClick={() => handleAdd(index)}>
            <db-icon type='plus-fill' />
          </bk-button>
          <bk-button
            text
            onClick={() => handleRemove(index)}>
            <db-icon type='minus-fill' />
          </bk-button>
        </div>
      ),
      width: 120,
    },
  ];

  const createData = () => ({
    mount_point: '',
    size: 0,
    type: '',
  });

  const handleCreate = () => {
    modelValue.value.push(createData());
  };
  const handleAdd = (index: number) => {
    modelValue.value.splice(index + 1, 0, createData());
  };

  const handleRemove = (index: number) => {
    modelValue.value.splice(index, 1);
  };

  searchDeviceClass()
    .then((res) => {
      deviceClass.value = res.map((item) => ({
        label: deviceClassDisplayMap[item as DeviceClass],
        value: item,
      }));
    })
    .finally(() => {
      isLoadDeviceClass.value = false;
    });

  defineExpose<Expose>({
    getValue() {
      if (modelValue.value.length === 0) {
        return;
      }
      const storageDevice = modelValue.value.reduce<StorageDevice>(
        (result, item) => ({
          ...result,
          [item.mount_point]: {
            disk_type: item.type,
            size: item.size,
          },
        }),
        {},
      );
      return {
        storage_device: storageDevice,
      };
    },
  });
</script>

<style lang="less">
  .resource-spec-storage-box {
    .bk-vxe-table {
      .vxe-cell {
        padding: 0 !important;

        .large-size {
          height: 42px;

          .bk-input {
            height: 42px;
          }
        }

        .bk-form-error-tips {
          top: 12px;
        }
      }

      .opertaions {
        .bk-button {
          margin-left: 18px;
          font-size: @font-size-normal;

          &:not(.is-disabled) i {
            color: @light-gray;

            &:hover {
              color: @gray-color;
            }
          }

          &.is-disabled {
            i {
              color: @disable-color;
            }
          }
        }
      }
    }

    .create-row {
      display: flex;
      height: 41px;
      font-size: 16px;
      flex: 1;
      cursor: pointer;
      justify-content: center;
      align-items: center;

      &:hover {
        color: #3a84ff;
      }
    }
  }
</style>
