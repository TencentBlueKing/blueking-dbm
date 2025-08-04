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
    :class="{
      'not-required': !isRequired,
    }">
    <div class="spec-form-item-label">
      {{ t('磁盘') }}
    </div>
    <div class="spec-form-item-content">
      <BkButton
        v-if="tableData.length === 0"
        v-bk-tooltips="{
          content: t('该规格已被使用，不允许修改'),
          disabled: editable,
        }"
        :disabled="!editable"
        @click="handleAddFirstRow">
        <DbIcon type="add" />
        <span style="font-size: 12px">{{ t('添加') }}</span>
      </BkButton>
      <EditableTable
        v-else
        ref="editableTableRef"
        :model="tableData">
        <EditableRow
          v-for="(item, index) in tableData"
          :key="index">
          <EditableColumn
            :append-rules="mountPointRules"
            field="mount_point"
            :label="t('挂载点')"
            :min-width="180"
            :required="isRequired"
            :width="200">
            <EditableInput
              v-model="item.mount_point"
              v-bk-tooltips="{
                content: t('该规格已被使用，不允许修改'),
                disabled: editable,
              }"
              :disabled="!editable"
              :placeholder="mountPointPlaceholder"
              @change="handleRowValueChange">
            </EditableInput>
          </EditableColumn>
          <EditableColumn
            :append-rules="minCapacityRules"
            field="min"
            :label="t('最小容量（G）')"
            :required="isRequired"
            :width="100">
            <EditableInput
              ref="minCapacityRef"
              v-model="item.min"
              v-bk-tooltips="{
                content: t('该规格已被使用，不允许修改'),
                disabled: editable,
              }"
              :disabled="!editable"
              :max="2147483647"
              :min="10"
              type="number"
              @change="handleRowValueChange" />
          </EditableColumn>
          <EditableColumn
            :append-rules="maxCapacityRules"
            field="max"
            :label="t('最大容量（G）')"
            :required="isRequired"
            :width="100">
            <EditableInput
              ref="maxCapacityRef"
              v-model="item.max"
              v-bk-tooltips="{
                content: t('该规格已被使用，不允许修改'),
                disabled: editable,
              }"
              :disabled="!editable"
              :max="2147483647"
              :min="10"
              type="number"
              @change="handleRowValueChange" />
          </EditableColumn>
          <EditableColumn
            :append-rules="diskTypRules"
            field="type"
            :label="t('磁盘类型')"
            :min-width="100"
            :required="isRequired"
            :width="120">
            <EditableSelect
              ref="diskTypeRef"
              v-model="item.type"
              v-bk-tooltips="{
                content: t('该规格已被使用，不允许修改'),
                disabled: editable,
              }"
              :disabled="!editable"
              :list="diskTypeList"
              @change="handleRowValueChange" />
          </EditableColumn>
          <OperationColumn
            v-if="editable"
            v-model:table-data="tableData"
            :create-row-method="createRowData" />
        </EditableRow>
      </EditableTable>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { searchDeviceClass } from '@services/source/ipchooser';

  import { DBTypes, DeviceClass, deviceClassDisplayMap } from '@common/const';

  interface InfoItem {
    max: string | number;
    min: string | number;
    mount_point: string;
    type: string;
  }

  interface IDataRow extends InfoItem {
    isSystemDrive?: boolean;
  }

  interface Props {
    data?: InfoItem[];
    dbType: string;
    editable: boolean;
    isRequired?: boolean;
  }

  type Emits = (e: 'table-value-change') => void;

  interface Exposes {
    getValue: () => Promise<InfoItem[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isRequired: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const createRowData = (data = {} as InfoItem) => ({
    max: data.max || ('' as string | number),
    min: data.min || ('' as string | number),
    mount_point: data.mount_point || '',
    type: data.type || '',
  });

  const editableTableRef = useTemplateRef('editableTableRef');

  const tableData = ref<IDataRow[]>([]);
  const diskTypeList = ref<{ label: string; value: string }[]>([]);

  const isSqlserver = computed(() => props.dbType === DBTypes.SQLSERVER);
  const mountPointList = computed(() => tableData.value.map((item) => item.mount_point));
  const mountPointPlaceholder = computed(() => (isSqlserver.value ? 'X:\\' : '/data123'));

  const mountPointRules = [
    {
      message: t('不能为空'),
      required: true,
      trigger: 'change',
      validator: (value: string, { rowData }: { rowData: IDataRow }) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !rowData.max && !rowData.min && !rowData.type) {
            return true;
          }
          if ((rowData.max || rowData.min || rowData.type) && !value) {
            return false;
          }
        }

        if (props.isRequired && !value) {
          return false;
        }

        return true;
      },
    },
    {
      message: '',
      trigger: 'change',
      validator: (value: string) => {
        if (!props.isRequired && !value) {
          return true;
        }
        if (isSqlserver.value) {
          return /[A-Z]:/.test(value) ? true : t('输入需符合正则_regx', { regx: '[A-Z]:\\' });
        }
        return /\/data(\d)*/.test(value) ? true : t('输入需符合正则_regx', { regx: '/data(\\d)*/' });
      },
    },
    {
      message: '',
      trigger: 'change',
      validator: (value: string) => {
        if (!props.isRequired && !value) {
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
      validator: (value: string, { rowData }: { rowData: IDataRow }) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !rowData.min && !rowData.mount_point && !rowData.type) {
            return true;
          }
          if ((rowData.min || rowData.mount_point || rowData.type) && !value) {
            return false;
          }
        }

        if (props.isRequired && !value) {
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
      validator: (value: string, { rowData }: { rowData: IDataRow }) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !rowData.max && !rowData.mount_point && !rowData.type) {
            return true;
          }
          if ((rowData.max || rowData.mount_point || rowData.type) && !value) {
            return false;
          }
        }

        if (props.isRequired && !value) {
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
      validator: (value: string, { rowData }: { rowData: IDataRow }) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !rowData.mount_point && !rowData.max && !rowData.min) {
            return true;
          }
          if ((rowData.mount_point || rowData.max || rowData.min) && !value) {
            return false;
          }
        }

        if (props.isRequired && !value) {
          return false;
        }

        return true;
      },
    },
  ];

  watch(
    () => props.data,
    (data) => {
      if (data && data.length) {
        tableData.value = data.map((item) => createRowData(item));
      }
    },
    {
      immediate: true,
    },
  );

  useRequest(searchDeviceClass, {
    onSuccess(data) {
      diskTypeList.value = data.map((item) => ({
        label: deviceClassDisplayMap[item as DeviceClass],
        value: item,
      }));
    },
  });

  const handleRowValueChange = () => {
    emits('table-value-change');
  };

  const handleAddFirstRow = () => {
    tableData.value = [createRowData()];
  };

  defineExpose<Exposes>({
    getValue: () =>
      tableData.value.length == 0
        ? Promise.resolve([])
        : editableTableRef.value!.validate().then((validateResult) => {
            if (validateResult) {
              return tableData.value.reduce<InfoItem[]>((prevList, row) => {
                if (row.mount_point && row.max && row.min && row.type) {
                  return prevList.concat({
                    max: row.max,
                    min: row.min,
                    mount_point: row.mount_point,
                    type: row.type,
                  });
                }
                return prevList;
              }, []);
            }
            return Promise.reject([]);
          }),
  });
</script>
<style lang="less" scoped>
  @import '../specFormItem.less';
</style>
