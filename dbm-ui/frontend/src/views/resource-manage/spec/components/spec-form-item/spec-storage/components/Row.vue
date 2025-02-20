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
  <tr>
    <td style="padding: 0">
      <RenderInput
        ref="mountPointRef"
        v-model="localValue.mount_point"
        v-bk-tooltips="{
          content: t('该规格已被使用，不允许修改'),
          disabled: !isEdit && !localValue.isSystemDrive,
        }"
        :disabled="isEdit || localValue.isSystemDrive"
        :placeholder="mountPointPlaceholder"
        :rules="mountPointRules" />
    </td>
    <td style="padding: 0">
      <RenderInput
        ref="minCapacityRef"
        v-model="localValue.size"
        v-bk-tooltips="{
          content: t('该规格已被使用，不允许修改'),
          disabled: !isEdit,
        }"
        :disabled="isEdit"
        :max="20000"
        :min="10"
        :rules="minCapacityRules"
        type="number" />
    </td>
    <td style="padding: 0; background-color: #fff">
      <RenderSelect
        ref="diskTypeRef"
        v-model="localValue.type"
        v-bk-tooltips="{
          content: t('该规格已被使用，不允许修改'),
          disabled: !props.isEdit,
        }"
        :disabled="isEdit"
        :list="diskTypeList"
        :rules="diskTypRules" />
    </td>
    <OperateColumn
      :removeable="false"
      :show-add="!isEdit"
      :show-remove="!isEdit"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  export interface InfoItem {
    mount_point: string;
    size: string | number;
    type: string;
  }

  export interface IDataRow extends InfoItem {
    isSystemDrive?: boolean;
    rowKey: string;
  }

  // 创建行数据
  export const createRowData = (data = {} as InfoItem) => ({
    mount_point: data.mount_point || '',
    rowKey: random(),
    size: data.size || ('' as string | number),
    type: data.type || '',
  });
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import RenderInput from '@components/render-table/columns/input/index.vue';
  import RenderSelect from '@components/render-table/columns/select/index.vue';

  interface Props {
    data: IDataRow;
    dbType: string;
    diskTypeList: { label: string; value: string }[];
    isEdit: boolean;
    isRequired?: boolean;
    mountPointList: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'value-change', params: InfoItem): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    isEdit: false,
    isRequired: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(props.data);
  const mountPointRef = ref<InstanceType<typeof RenderInput>>();
  const minCapacityRef = ref<InstanceType<typeof RenderInput>>();
  const diskTypeRef = ref<InstanceType<typeof RenderSelect>>();

  const isSqlserver = computed(() => props.dbType === DBTypes.SQLSERVER);

  const mountPointPlaceholder = computed(() => (isSqlserver.value ? 'X:\\' : '/data123'));

  const mountPointRules = [
    {
      message: t('不能为空'),
      validator: (value: string) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !localValue.value.size && !localValue.value.type) {
            return true;
          }

          if ((localValue.value.size || localValue.value.type) && !value) {
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
      message: t('输入需符合正则_regx', { regx: '/data(\\d)*/' }),
      validator: (value: string) => {
        if (localValue.value.isSystemDrive || isSqlserver.value) {
          return true;
        }
        return /\/data(\d)*/.test(value);
      },
    },
    // 仅针对sqlserver
    {
      message: t('输入需符合正则_regx', { regx: '[A-Z]:\\' }),
      validator: (value: string) => {
        if (isSqlserver.value) {
          return /[A-Z]:/.test(value);
        }

        return true;
      },
    },
    {
      message: () => t('挂载点name重复', { name: localValue.value.mount_point }),
      validator: (value: string) => props.mountPointList.filter((item) => item === value).length < 2,
    },
  ];

  const minCapacityRules = [
    {
      message: t('不能为空'),
      validator: (value: string) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !localValue.value.mount_point && !localValue.value.type) {
            return true;
          }

          if ((localValue.value.mount_point || localValue.value.type) && !value) {
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
      validator: (value: string) => {
        // 非必填且所有输入框没有输入
        if (!props.isRequired) {
          if (!value && !localValue.value.mount_point && !localValue.value.size) {
            return true;
          }

          if ((localValue.value.mount_point || localValue.value.size) && !value) {
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

  let rawRowData: IDataRow;

  watch(
    () => props.data,
    (data) => {
      rawRowData = _.cloneDeep(data);
    },
    {
      immediate: true,
    },
  );

  watch(
    localValue,
    () => {
      const { mount_point: mountPoint, size, type } = localValue.value;
      const { mount_point: rawMountPoint, size: rawSize, type: rawType } = rawRowData;
      if (mountPoint !== rawMountPoint || size === rawSize || type === rawType) {
        emits('value-change', localValue.value);
      }
    },
    {
      deep: true,
    },
  );

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    emits('remove');
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        mountPointRef.value!.getValue(),
        minCapacityRef.value!.getValue(),
        diskTypeRef.value!.getValue(),
      ]).then(() => {
        const { mount_point: mountPoint, size, type } = localValue.value;
        return {
          mount_point: mountPoint,
          size,
          type,
        };
      });
    },
  });
</script>
