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
      v-model="localValue"
      :placeholder="$t('请输入或选择集群')"
      :rules="rules"
      @submit="handleInputFinish" />
  </div>
</template>

<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { queryClusters } from '@services/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { domainRegex } from '@common/regex';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import { random } from '@utils';

  interface Props {
    data?: string;
    checkDuplicate?: boolean;
  }

  interface Emits {
    (e: 'onInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    checkDuplicate: true,
  });
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const localClusterId = ref(0);
  const localValue = ref(props.data);
  const editRef = ref();
  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const rules = [
    {
      validator: (value: string) => Boolean(_.trim(value)),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>  domainRegex.test(_.trim(value)),
      message: t('目标集群输入格式有误'),
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
        if (!props.checkDuplicate) return true;
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

  // 获取关联集群
  watch(localClusterId, () => {
    if (!localClusterId.value) {
      return;
    }
    clusterIdMemo[instanceKey][localClusterId.value] = true;
  }, {
    immediate: true,
  });

  const handleInputFinish = (value: string) => {
    const realValue = _.trim(value);
    localValue.value = realValue;
    emits('onInputFinish', realValue);
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });

</script>
<style lang="less" scoped>
  .render-cluster-box {
    position: relative;
  }
</style>
