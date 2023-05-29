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
  <div class="render-cluster-box">
    <TableEditInput
      ref="editRef"
      v-model="localDomain"
      multi-input
      :placeholder="$t('请输入集群_使用换行分割一次可输入多个')"
      :rules="rules"
      @multi-input="handleMultiInput" />
  </div>
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import {
    onBeforeUnmount,
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  import { random } from '@utils';

  interface Props {
    modelValue?: {
      id: number,
      domain: string,
      cloudId: null | number
    },
  }

  interface Emits {
    (e: 'inputCreate', value: Array<string>): void,
    (e: 'idChange', value: { id: number, cloudId: number | null }): void,
  }

  interface Exposes {
    getValue: () => Array<number>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const instanceKey = `render_cluster_instance_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();

  const localClusterId = ref(0);
  const localDomain = ref('');

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        emits('idChange', {
          id: 0,
          cloudId: null,
        });
        return false;
      },
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => queryClusters({
        cluster_filters: [
          {
            immute_domain: value,
          },
        ],
        bk_biz_id: currentBizId,
      }).then((data) => {
        if (data.length > 0) {
          localClusterId.value = data[0].id;
          emits('idChange', {
            id: localClusterId.value,
            cloudId: data[0].bk_cloud_id,
          });
          return true;
        }
        emits('idChange', {
          id: 0,
          cloudId: null,
        });
        return false;
      }),
      message: t('目标集群不存在'),
    },
    {
      validator: () => {
        const currentClusterSelectMap = clusterIdMemo[instanceKey];
        const otherClusterMemoMap = { ...clusterIdMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce((result, item) => ({
          ...result,
          ...item,
        }), {} as Record<string, boolean>);

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
  watch(() => props.modelValue, () => {
    const {
      id = 0,
      domain = '',
    } = props.modelValue || {};
    localClusterId.value = id;
    localDomain.value = domain;
  }, {
    immediate: true,
  });

  // 获取关联集群
  watch(localClusterId, () => {
    if (!localClusterId.value) {
      return;
    }
    clusterIdMemo[instanceKey][localClusterId.value] = true;
  }, {
    immediate: true,
  });

  const handleMultiInput = (list: Array<string>) => {
    emits('inputCreate', list);
  };

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      const result = {
        cluster_id: localClusterId.value,
      };
      // 用户输入未完成验证
      if (editRef.value) {
        return editRef.value
          .getValue()
          .then(() => result);
      }
      // 用户输入错误
      if (!localClusterId.value) {
        return Promise.reject();
      }
      return Promise.resolve(result);
    },
  });
</script>
<style lang="less" scoped>
  @keyframes rotate-loading {
    0% {
      transform: rotateZ(0);
    }

    100% {
      transform: rotateZ(360deg);
    }
  }

  .render-cluster-box {
    position: relative;

    &.is-editing {
      padding: 0;
    }

    .render-cluster-domain {
      display: flex;
      height: 20px;
      padding-left: 16px;
      line-height: 20px;
      align-items: center;

      .relate-loading {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-left: 4px;
        color: #3a84ff;
        animation: rotate-loading 1s linear infinite;
      }

      .relate-btn {
        display: flex;
        width: 20px;
        height: 20px;
        margin-left: 4px;
        color: #3a84ff;
        cursor: pointer;
        background: #e1ecff;
        border-radius: 2px;
        align-items: center;
        justify-content: center;
      }
    }

    .related-cluster-list {
      padding-left: 24px;
      font-size: 12px;
      line-height: 22px;
      color: #979ba5;
    }
  }
</style>
