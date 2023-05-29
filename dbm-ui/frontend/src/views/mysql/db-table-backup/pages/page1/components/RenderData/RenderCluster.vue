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

  import type { IDataRow } from './Row.vue';

  interface Props {
    modelValue?: IDataRow['clusterData'],
  }

  interface Emits {
    (e: 'inputCreate', value: Array<string>): void,
    (e: 'idChange', value: number): void,
  }

  interface Exposes {
    getValue: () => Array<number>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { currentBizId } = useGlobalBizs();

  const editRef = ref();

  const localClusterId = ref(0);
  const localDomain = ref('');
  const isShowEdit = ref(true);

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        emits('idChange', 0);
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
          return true;
        }
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
        emits('idChange', localClusterId.value);
        return true;
      },
      message: t('目标集群重复'),
    },
  ];

  // 同步外部值
  watch(() => props.modelValue, () => {
    if (props.modelValue) {
      localClusterId.value = props.modelValue.id;
      localDomain.value = props.modelValue.domain;
      isShowEdit.value = false;
    } else {
      isShowEdit.value = true;
    }
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
      return editRef.value
        .getValue()
        .then(() => ({
          cluster_id: localClusterId.value,
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-cluster-box {
    position: relative;
  }
</style>
