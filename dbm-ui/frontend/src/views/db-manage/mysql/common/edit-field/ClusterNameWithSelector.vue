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
    v-model="localDomain"
    class="cluster-name-with-selector"
    :placeholder="t('请输入集群域名或从表头批量选择')"
    :rules="rules"
    @blur="() => (isFocused = false)"
    @error="handleInputError"
    @focus="() => (isFocused = true)"
    @submit="handleInputChange">
    <template #suspend>
      <BkPopover
        v-if="!isFocused"
        :content="t('选择集群')"
        placement="top"
        :popover-delay="0">
        <div class="edit-btn-wraper">
          <div
            class="edit-btn"
            @click="handleClickSeletor">
            <div class="edit-btn-inner">
              <DbIcon
                class="select-icon"
                type="host-select" />
            </div>
          </div>
        </div>
      </BkPopover>
    </template>
  </TableEditInput>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="tabList"
    only-one-type
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { queryClusters } from '@services/source/mysqlCluster';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  export interface ClusterBasicInfo {
    id: number;
    domain: string;
    bizId: number;
    cloudId: number;
    cloudName: string;
    clusterType: string;
  }

  interface Props {
    modelValue?: {
      id: number;
      domain: string;
      type?: string;
    };
    onlyOneType?: boolean;
    clusterTypes?: string[];
    tabs?: 'tendbha' | 'tendbsingle' | 'both';
  }

  interface Emits {
    (e: 'clusterChange', info: ClusterBasicInfo): void;
    (e: 'error', value: boolean): void;
  }

  interface Exposes {
    getValue: () => Promise<{ cluster_id: number }>;
    focus: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    odelValue: undefined,
    onlyOneType: false,
    clusterTypes: () => [],
    tabs: 'tendbha',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const inputRef = ref();
  const isFocused = ref(false);
  const isShowSelector = ref(false);
  const selectedClusters = shallowRef<{ [key: string]: Array<any> }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: {
      multiple: false,
    },
    [ClusterTypes.TENDBSINGLE]: {
      multiple: false,
    },
  } as unknown as Record<string, TabConfig>;

  const localClusterId = ref(0);
  const localDomain = ref('');

  const tabList = computed(() => {
    if (props.tabs === 'tendbha') {
      return [ClusterTypes.TENDBHA];
    }
    if (props.tabs === 'tendbsingle') {
      return [ClusterTypes.TENDBSINGLE];
    }
    return [ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE];
  });

  let isSkipInputFinish = false;

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>
        queryClusters({
          cluster_filters: [
            {
              immute_domain: value,
            },
          ],
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }).then((data) => {
          if (data.length > 0) {
            const {
              id,
              master_domain: domain,
              bk_biz_id: bizId,
              bk_cloud_id: cloudId,
              bk_cloud_name: cloudName,
              cluster_type: clusterType,
            } = data[0];
            localClusterId.value = id;
            if (!isSkipInputFinish) {
              emits('clusterChange', {
                id,
                domain,
                bizId,
                cloudId,
                cloudName,
                clusterType,
              });
            }
            return true;
          }
          return false;
        }),
      message: t('目标集群不存在'),
    },
    {
      validator: () => {
        if (!props.onlyOneType) {
          return true;
        }
        const types = new Set(props.clusterTypes.filter((item) => !!item));
        return types.size === 1;
      },
      message: t('只允许提交一种集群类型'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = clusterIdMemo[instanceKey];
        const otherClusterMemoMap = { ...clusterIdMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce(
          (result, item) => ({
            ...result,
            ...item,
          }),
          {} as Record<string, boolean>,
        );

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('目标集群重复'),
    },
  ];

  // 同步外部值
  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localClusterId.value = props.modelValue.id;
        localDomain.value = props.modelValue.domain;
      }
    },
    {
      immediate: true,
      deep: true,
    },
  );

  // 获取关联集群
  watch(
    localClusterId,
    () => {
      if (!localClusterId.value) {
        return;
      }
      clusterIdMemo[instanceKey][localClusterId.value] = true;
    },
    {
      immediate: true,
    },
  );

  const handleClickSeletor = () => {
    isShowSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    if (value === '') {
      clusterIdMemo[instanceKey] = {};
    }
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: TendbhaModel[] }) => {
    selectedClusters.value = selected;
    const list = Object.keys(selected).reduce((list: TendbhaModel[], key) => list.concat(...selected[key]), []);
    localDomain.value = list[0].master_domain;
    window.changeConfirm = true;
    setTimeout(() => {
      inputRef.value.getValue();
    });
  };

  const handleInputError = (value: boolean) => {
    emits('error', value);
  };

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      isSkipInputFinish = true;
      return inputRef.value
        .getValue()
        .then(() => ({
          cluster_id: localClusterId.value,
        }))
        .finally(() => {
          isSkipInputFinish = false;
        });
    },
    focus() {
      inputRef.value.focus();
    },
  });
</script>
<style lang="less" scoped>
  .cluster-name-with-selector {
    &:hover {
      :deep(.edit-btn-wraper) {
        display: block;
      }
    }
  }

  .edit-btn-wraper {
    display: none;

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
  }
</style>
