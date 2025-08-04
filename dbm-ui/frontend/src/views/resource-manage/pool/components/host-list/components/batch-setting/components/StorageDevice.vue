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
    <EditableTable
      ref="editableTableRef"
      :model="modelValue">
      <EditableRow
        v-for="(item, index) in modelValue"
        :key="index">
        <EditableColumn
          :append-rules="mountPointRules"
          field="mount_point"
          :label="t('挂载点')"
          :min-width="180"
          required>
          <EditableInput
            v-model="item.mount_point"
            placeholder="/data123">
          </EditableInput>
        </EditableColumn>
        <EditableColumn
          :append-rules="minCapacityRules"
          field="min"
          :label="t('最小容量（G）')"
          required
          :width="150">
          <EditableInput
            ref="minCapacityRef"
            v-model="item.min"
            :max="2147483647"
            :min="10"
            type="number" />
        </EditableColumn>
        <EditableColumn
          :append-rules="maxCapacityRules"
          field="max"
          :label="t('最大容量（G）')"
          required
          :width="150">
          <EditableInput
            ref="maxCapacityRef"
            v-model="item.max"
            :max="2147483647"
            :min="10"
            type="number" />
        </EditableColumn>
        <EditableColumn
          :append-rules="diskTypRules"
          field="type"
          :label="t('磁盘类型')"
          :min-width="100"
          required
          :width="120">
          <EditableSelect
            ref="diskTypeRef"
            v-model="item.type"
            :list="diskTypeList" />
        </EditableColumn>
        <OperationColumn
          v-model:table-data="modelValue"
          :create-row-method="createRowData" />
      </EditableRow>
    </EditableTable>
  </div>
</template>
<script lang="tsx">
  export interface IStorageDeviceItem {
    max: number;
    min: number;
    mount_point: string;
    type: string;
  }

  export const createRowData = (data = {} as IStorageDeviceItem) => ({
    max: data.max || ('' as string | number),
    min: data.min || ('' as string | number),
    mount_point: data.mount_point || '',
    type: data.type || '',
  });
</script>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateResource } from '@services/source/dbresourceResource';
  import { searchDeviceClass } from '@services/source/ipchooser';

  import { DeviceClass, deviceClassDisplayMap } from '@common/const';

  type StorageDevice = NonNullable<ServiceParameters<typeof updateResource>['storage_device']>;

  interface Expose {
    getValue: () => Promise<{
      storage_device: StorageDevice;
    }>;
  }

  const modelValue = defineModel<IStorageDeviceItem[]>({
    required: true,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTableRef');

  const diskTypeList = ref<{ label: string; value: string }[]>([]);

  const mountPointList = computed(() => modelValue.value.map((item) => item.mount_point));

  const mountPointRules = [
    {
      message: t('不能为空'),
      required: true,
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IStorageDeviceItem }) => {
        if (!value && !rowData.max && !rowData.min && !rowData.type) {
          return true;
        }
        if ((rowData.max || rowData.min || rowData.type) && !value) {
          return false;
        }
        if (!value) {
          return false;
        }
        return true;
      },
    },
    {
      message: t('输入需符合正则_regx', { regx: '/data(\\d)*/' }),
      trigger: 'change',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return /\/data(\d)*/.test(value) ? true : t('输入需符合正则_regx', { regx: '/data(\\d)*/' });
      },
    },
    {
      message: '',
      trigger: 'change',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return mountPointList.value.filter((item) => item === value).length < 2
          ? true
          : t('挂载点name重复', { name: value });
      },
    },
  ];

  const maxCapacityRules = [
    {
      message: t('不能为空'),
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IStorageDeviceItem }) => {
        if (!value && !rowData.min && !rowData.mount_point && !rowData.type) {
          return true;
        }
        if ((rowData.min || rowData.mount_point || rowData.type) && !value) {
          return false;
        }
        if (!value) {
          return false;
        }
        return true;
      },
    },
  ];

  const minCapacityRules = [
    {
      message: t('不能为空'),
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IStorageDeviceItem }) => {
        if (!value && !rowData.max && !rowData.mount_point && !rowData.type) {
          return true;
        }
        if ((rowData.max || rowData.mount_point || rowData.type) && !value) {
          return false;
        }
        if (!value) {
          return false;
        }
        return true;
      },
    },
  ];

  const diskTypRules = [
    {
      message: t('不能为空'),
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IStorageDeviceItem }) => {
        if (!value && !rowData.mount_point && !rowData.max && !rowData.min) {
          return true;
        }
        if ((rowData.mount_point || rowData.max || rowData.min) && !value) {
          return false;
        }
        if (!value) {
          return false;
        }
        return true;
      },
    },
  ];

  useRequest(searchDeviceClass, {
    onSuccess(data) {
      diskTypeList.value = data.map((item) => ({
        label: deviceClassDisplayMap[item as DeviceClass],
        value: item,
      }));
    },
  });

  defineExpose<Expose>({
    getValue() {
      return editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          const storageDevice = modelValue.value.reduce<StorageDevice>(
            (result, item) => ({
              ...result,
              [item.mount_point]: {
                disk_type: item.type,
                max: item.max,
                min: item.min,
              },
            }),
            {},
          );
          return {
            storage_device: storageDevice,
          };
        }

        return Promise.reject();
      });
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
