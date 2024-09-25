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
      :placeholder="t('请输入')"
      :rules="rules"
      @focus="handleFocus" />
  </div>
</template>
<!-- <script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script> -->
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';

  import TableEditInput from '@views/db-manage/tendb-cluster/common/edit/Input.vue';

  // import { random } from '@utils';
  import type { IDataRow } from './Row.vue';

  interface Props {
    modelValue?: IDataRow['clusterData'];
  }

  interface Emits {
    (e: 'clusterInputFinish', value: TendbClusterModel): void;
  }

  interface Exposes {
    getValue: (isSubmit: boolean) => Promise<{
      cluster_id: number;
    }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // const instanceKey = `render_cluster_${random()}`;
  // clusterIdMemo[instanceKey] = {};

  const editRef = ref<InstanceType<typeof TableEditInput>>();

  const localClusterId = ref(0);
  const localDomain = ref('');
  const isShowEdit = ref(true);

  let isSkipInputFinish = false;

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>
        getTendbClusterList({ exact_domain: value }).then((data) => {
          if (data.results.length > 0) {
            if (!isSkipInputFinish) {
              emits('clusterInputFinish', data.results[0]);
            }
            localClusterId.value = data.results[0].id;
            return true;
          }
          return false;
        }),
      message: t('目标集群不存在'),
    },
    // {
    //   validator: () => {
    //     const currentClusterSelectMap = clusterIdMemo[instanceKey];
    //     const otherClusterMemoMap = { ...clusterIdMemo };
    //     delete otherClusterMemoMap[instanceKey];

    //     const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce((result, item) => ({
    //       ...result,
    //       ...item,
    //     }), {} as Record<string, boolean>);

    //     const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
    //     for (let i = 0; i < currentSelectClusterIdList.length; i++) {
    //       if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
    //         return false;
    //       }
    //     }
    //     return true;
    //   },
    //   message: t('目标集群重复'),
    // },
  ];

  // 同步外部值
  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue) {
        localClusterId.value = props.modelValue.id;
        localDomain.value = props.modelValue.master_domain;
        isShowEdit.value = false;
      } else {
        isShowEdit.value = true;
      }
    },
    {
      immediate: true,
    },
  );

  // 获取关联集群
  watch(
    localClusterId,
    () => {
      if (!localClusterId.value) {
        return;
      }
      // clusterIdMemo[instanceKey][localClusterId.value] = true;
    },
    {
      immediate: true,
    },
  );

  // onBeforeUnmount(() => {
  //   delete clusterIdMemo[instanceKey];
  // });

  const handleFocus = () => {
    isSkipInputFinish = false;
  };

  defineExpose<Exposes>({
    getValue(isSubmit = false) {
      isSkipInputFinish = isSubmit;
      return editRef.value!.getValue().then(() => ({
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
