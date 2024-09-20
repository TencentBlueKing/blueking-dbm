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
  <TableEditInput
    ref="inputRef"
    v-model="modelValue"
    :autosize="{
      minRows: 1,
      maxRows: 6,
    }"
    :placeholder="t('请选择或输入')"
    :resize="false"
    :rules="rules"
    type="textarea"
    @blur="() => (isFocused = false)"
    @focus="() => (isFocused = true)">
    <template #suspend>
      <BkPopover
        v-if="!isFocused"
        :content="t('选择集群')"
        placement="top"
        :popover-delay="0">
        <div
          class="edit-btn"
          @click="handleClickSeletor">
          <div class="edit-btn-inner">
            <DbIcon
              class="select-icon"
              type="host-select" />
          </div>
        </div>
      </BkPopover>
    </template>
  </TableEditInput>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import TableEditInput from '@components/render-table/columns/input/index.vue';
  import { type Rules } from '@components/render-table/hooks/useValidtor';

  interface Props {
    sourceClusterId: number;
    rules?: Rules;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const inputRef = ref();
  const isFocused = ref(false);
  const isShowSelector = ref(false);
  const selectedClusters = shallowRef<{ [key: string]: Array<any> }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: {
      showPreviewResultTitle: true,
      disabledRowConfig: [
        {
          handler: (data: TendbhaModel) => data.id === props.sourceClusterId,
          tip: t('不能选择源集群'),
        },
      ],
    },
    [ClusterTypes.TENDBSINGLE]: {
      showPreviewResultTitle: true,
      disabledRowConfig: [
        {
          handler: (data: TendbhaModel) => data.id === props.sourceClusterId,
          tip: t('不能选择源集群'),
        },
      ],
    },
  } as unknown as Record<string, TabConfig>;

  const handleClickSeletor = () => {
    isShowSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: TendbhaModel[] }) => {
    selectedClusters.value = selected;
    const list = Object.keys(selected).reduce((list: TendbhaModel[], key) => list.concat(...selected[key]), []);
    modelValue.value = list.map((item) => item.master_domain).join('\n');
    window.changeConfirm = true;
    setTimeout(() => {
      inputRef.value.getValue();
    });
  };

  defineExpose<Exposes>({
    // 获取值
    getValue() {
      return inputRef.value.getValue().then(() => modelValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .edit-btn {
    display: flex;
    width: 24px;
    height: 40px;
    align-items: center;

    .edit-btn-inner {
      display: flex;
      width: 24px;
      height: 24px;
      cursor: pointer;
      border-radius: 2px;
      align-items: center;
      justify-content: center;

      .select-icon {
        font-size: 16px;
        color: #979ba5;
      }

      &:hover {
        background: #f0f1f5;

        .select-icon {
          color: #3a84ff;
        }
      }
    }
  }
</style>
