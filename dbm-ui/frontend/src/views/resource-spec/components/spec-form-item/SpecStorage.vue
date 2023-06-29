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
  <div
    class="spec-mem spec-form-item"
    :class="{'not-required': !isRequired}">
    <div class="spec-form-item__label">
      {{ $t('磁盘') }}
    </div>
    <div class="spec-form-item__content">
      <DbOriginalTable
        :border="['row', 'col', 'outer']"
        class="custom-edit-table"
        :columns="columns"
        :data="tableData" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { searchDeviceClass } from '@services/ip';

  interface StorageSpecItem {
    mount_point: string,
    size: string | number,
    type: string,
  }

  interface TableColumnData {
    data: StorageSpecItem,
    index: number
  }

  interface Props {
    modelValue: StorageSpecItem[],
    isEdit: boolean,
    isRequired: boolean
  }

  interface Emits {
    (e: 'update:modelValue', value: StorageSpecItem[]): void
  }

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
    isRequired: true,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tableData = ref([...props.modelValue]);
  const deviceClass = ref<{label: string, value: string}[]>([]);
  const isLoadDeviceClass = ref(true);
  const mountPointRules = (data: StorageSpecItem) => {
    // 非必填
    if (!props.isRequired && !data.mount_point && !data.size && !data.type) {
      return [];
    }

    return [
      {
        validator: (value: string) => /data(\d)*/.test(value),
        message: t('输入需符合正则_regx', { regx: '/data(\\d)*/' }),
        trigger: 'blur',
      },
      {
        validator: (value: string) => tableData.value.filter(item => item.mount_point === value).length < 2,
        message: () => t('挂载点name重复', { name: data.mount_point }),
        trigger: 'blur',
      },
    ];
  };
  const sizeRules = (data: StorageSpecItem) => {
    // 非必填且其他输入框没有输入
    if (!props.isRequired && !data.mount_point && !data.type) {
      return [];
    }

    return [
      {
        required: true,
        message: 'test',
        validator: (value: string) => !!value,
        trigger: 'blur',
      },
    ];
  };
  const typeRules = (data: StorageSpecItem) => {
    // 非必填且其他输入框没有输入
    if (!props.isRequired && !data.mount_point && !data.size) {
      return [];
    }

    return [
      {
        required: true,
        message: 'test',
        validator: (value: string) => !!value,
        trigger: 'change',
      },
    ];
  };
  const columns = [
    {
      field: 'mount_point',
      label: t('挂载点'),
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          property={`storage_spec.${index}.mount_point`}
          error-display-type="tooltips"
          required={props.isRequired}
          rules={mountPointRules(data)}>
          <div
            v-bk-tooltips={{
              content: t('不支持修改'),
              disabled: !props.isEdit,
            }}>
            <bk-input
              class="large-size"
              v-model={data.mount_point}
              placeholder="/data123"
              disabled={props.isEdit} />
          </div>
        </bk-form-item>
      ),
    },
    {
      field: 'size',
      label: t('最小容量G'),
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          property={`storage_spec.${index}.size`}
          error-display-type="tooltips"
          required={props.isRequired}
          rules={sizeRules(data)}>
          <div
            v-bk-tooltips={{
              content: t('不支持修改'),
              disabled: !props.isEdit,
            }}>
            <bk-input
              class="large-size"
              v-model={data.size}
              type="number"
              show-control={false}
              min={10}
              disabled={props.isEdit} />
          </div>
        </bk-form-item>
      ),
    },
    {
      field: 'type',
      label: t('磁盘类型'),
      render: ({ data, index }: TableColumnData) => (
        <bk-form-item
          property={`storage_spec.${index}.type`}
          error-display-type="tooltips"
          required={props.isRequired}
          rules={typeRules(data)}>
          <div
            v-bk-tooltips={{
              content: t('不支持修改'),
              disabled: !props.isEdit,
            }}>
            <bk-select
              class="large-size"
              v-model={data.type}
              clearable={false}
              disabled={props.isEdit}
              loading={isLoadDeviceClass.value}>
              {
                deviceClass.value.map(item => <bk-option label={item.label} value={item.value} />)
              }
            </bk-select>
          </div>
        </bk-form-item>
      ),
    },
    {
      field: '',
      label: t('操作'),
      width: 120,
      render: ({ index }: TableColumnData) => (
        <div class="opertaions">
          <bk-button
            text
            disabled={props.isEdit}
            onClick={() => handleAdd(index)}>
            <db-icon type="plus-fill" />
          </bk-button>
          <bk-button
            text
            disabled={tableData.value.length === 1 || props.isEdit}
            onClick={() => handleRemove(index)}>
            <db-icon type="minus-fill" />
          </bk-button>
        </div>
      ),
    },
  ];

  const createData = () => ({
    mount_point: '',
    size: '' as string | number,
    type: '',
  });

  const handleAdd = (index: number) => {
    tableData.value.splice(index + 1, 0, createData());
  };

  const handleRemove = (index: number) => {
    tableData.value.splice(index, 1);
  };

  watch(tableData, () => {
    emits('update:modelValue', tableData.value.map(item => ({
      ...item,
      size: Number(item.size),
    })));
  }, { deep: true });

  searchDeviceClass()
    .then((res) => {
      deviceClass.value = res.map(item => ({
        label: item,
        value: item,
      }));
    })
    .finally(() => {
      isLoadDeviceClass.value = false;
    });
</script>

<style lang="less" scoped>
  @import "./specFormItem.less";

  :deep(.bk-table-body) {
    .cell {
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
</style>
