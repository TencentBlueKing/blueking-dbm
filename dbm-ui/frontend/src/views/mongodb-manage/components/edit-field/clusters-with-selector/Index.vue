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
  <div class="render-host-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="t('请选择或输入')"
      :rules="rules"
      @click-seletor="handleOpenSeletor" />
  </div>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[clusterType]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongoDBModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector, {
    type TabItem,
  } from '@components/cluster-selector-new/Index.vue';

  import TableEditInput from './Input.vue';

  interface Props {
    clusterType: ClusterTypes,
    data?: string;
  }

  interface Emits {
    (e: 'change', value: MongoDBModel[]): void
  }

  interface Exposes {
    getValue: () => Promise<number[]>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => ([]),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isShowSelector = ref(false);
  const localValue = ref(props.data);
  const editRef = ref();
  const localClusterIds = ref<number[]>([]);

  const selectedClusters = shallowRef<{[key: string]: Array<any>}>({
    [ClusterTypes.MONGO_REPLICA_SET]: [],
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const tabListConfig = computed(() => (props.clusterType === ClusterTypes.MONGO_REPLICA_SET ? {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      multiple: true,
    },
  } : {
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      multiple: false,
    },
  }) as unknown as Record<ClusterTypes, TabItem>);

  const rules = [
    {
      validator: (value: string) => value.split(',').every(domain => Boolean(domain)),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => value.split(',').every(domain => domainRegex.test(domain)),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: (value: string) => getMongoList({
        domains: value,
      }).then((data) => {
        if (data.results.length === value.split(',').length) {
          localClusterIds.value = data.results.map(item => item.id);
          return true;
        }
        return false;
      }),
      message: t('目标集群不存在'),
    },
  ];

  watch(() => props.data, (data) => {
    localValue.value = data;
  }, {
    immediate: true,
  });

  const handleOpenSeletor = () => {
    isShowSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: MongoDBModel[] }) => {
    selectedClusters.value = selected;
    const list = selected[props.clusterType];
    localValue.value = list.map(item => item.master_domain).join(',');
    emits('change', list);
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (localClusterIds.value));
    },
  });

</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;
    
    :deep(.is-error) {
      .error-icon {
        top: auto;
        top: 50%;
        right: auto;
        left: 50%;
        transform: translate(-50%, -50%);
      }
    }
  }
</style>
