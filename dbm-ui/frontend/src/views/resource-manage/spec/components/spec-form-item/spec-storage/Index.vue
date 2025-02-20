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
          disabled: !isEdit,
        }"
        :disabled="isEdit"
        @click="handleAddFirstRow">
        <DbIcon type="add" />
        <span style="font-size: 12px">{{ t('添加') }}</span>
      </BkButton>
      <div
        v-else
        style="width: 616px">
        <RenderData class="disk-table">
          <RenderDataRow
            v-for="(item, index) in tableData"
            :key="item.rowKey"
            ref="rowRefs"
            :data="item"
            :db-type="dbType"
            :disk-type-list="diskTypeList"
            :is-edit="isEdit"
            :is-required="isRequired"
            :mount-point-list="mountPointList"
            @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
            @remove="handleRemove(index)"
            @value-change="handleRowValueChange" />
        </RenderData>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { searchDeviceClass } from '@services/source/ipchooser';

  import RenderData from './components/RenderTable.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  interface Props {
    data?: InfoItem[];
    dbType: string;
    isEdit?: boolean;
    isRequired?: boolean;
  }

  type Emits = (e: 'table-value-change', params?: InfoItem) => void;

  interface Exposes {
    getValue: () => Promise<InfoItem[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isEdit: false,
    isRequired: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rowRefs = ref();
  const tableData = ref<IDataRow[]>([]);
  const diskTypeList = ref<{ label: string; value: string }[]>([]);

  const mountPointList = computed(() => tableData.value.map((item) => item.mount_point));

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
        label: item === 'ALL' ? t('无限制') : item,
        value: item,
      }));
    },
  });

  const handleRowValueChange = (data: InfoItem) => {
    emits('table-value-change', data);
  };

  const handleAddFirstRow = () => {
    tableData.value = [createRowData()];
  };

  // 追加一行
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
    emits('table-value-change');
  };

  // 删除一行
  const handleRemove = (index: number) => {
    tableData.value.splice(index, 1);
    emits('table-value-change');
  };

  defineExpose<Exposes>({
    getValue: () => Promise.all(rowRefs.value ? rowRefs.value.map((item: any) => item.getValue()) : []),
  });
</script>
<style lang="less" scoped>
  @import '../specFormItem.less';

  .disk-table {
    &::-webkit-scrollbar {
      background: #f5f7fa;
    }
  }
</style>
