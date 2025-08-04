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
          field="size"
          :label="t('容量（G）')"
          required
          :width="200">
          <EditableInput
            ref="sizeCapacityRef"
            v-model="item.size"
            :min="1"
            type="number" />
        </EditableColumn>
        <EditableColumn
          field="type"
          :label="t('数据盘类型')"
          required
          :width="200">
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
    mount_point: string;
    size: number;
    type: string;
  }

  export const createRowData = (data = {} as IStorageDeviceItem) => ({
    mount_point: data.mount_point || '',
    size: data.size || ('' as string | number),
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

  useRequest(searchDeviceClass, {
    onSuccess(data) {
      diskTypeList.value = data
        .map((item) => ({
          label: deviceClassDisplayMap[item as DeviceClass],
          value: item,
        }))
        .filter((item) => item.value !== 'ALL');
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
                size: item.size,
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
