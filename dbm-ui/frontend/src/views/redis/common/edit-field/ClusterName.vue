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
  <div class="cluster-name-box">
    <TableEditInput
      ref="editRef"
      v-model="localValue"
      :placeholder="$t('请输入或选择集群')"
      :rules="rules"
      @submit="handleInputFinish" />
    <!-- <BkPopover
      :content="t('从集群列表选择')"
      placement="top"
      :popover-delay="0">
      <div
        class="edit-btn"
        @click="handleOpenClusterSeletor">
        <div class="edit-btn-inner">
          <DbIcon
            class="select-icon"
            type="host-select" />
        </div>
      </div>
    </BkPopover> -->
  </div>
  <!-- <ClusterSelector
    v-model:is-show="isShowSelector"
    is-radio-mode
    :selected="selectedClusters"
    :tab-list="clusterSelectorTabList"
    @change="handelClusterChange" /> -->
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  // import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';

  // import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  // import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  interface Props {
    data?: string;
    inputed?: string[];
  }

  interface Emits {
    (e: 'onInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => ([]),
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // const isShowSelector = ref(false);
  const localValue = ref(props.data);
  const editRef = ref();

  // const selectedClusters = shallowRef<{[key: string]: Array<RedisModel>}>({ [ClusterTypes.REDIS]: [] });

  // const clusterSelectorTabList = [ClusterTypes.REDIS];
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>  domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: async (value: string) => {
        // TODO: 使用精确查询接口替换
        const result = await getRedisList({ domain: value });
        return result.results.filter(item => item.master_domain === value).length > 0;
      },
      message: t('目标集群不存在'),
    },
    {
      validator: (value: string) => props.inputed.filter(item => item === value).length < 2,
      message: t('目标集群重复'),
    },
  ];

  watch(() => props.data, (data) => {
    localValue.value = data;
    // selectedClusters.value[ClusterTypes.REDIS] = [{
    //   master_domain: data,
    // } as RedisModel];
  }, {
    immediate: true,
  });

  const handleInputFinish = (value: string) => {
    // editRef.value.getValue().then(() => {
    emits('onInputFinish', value);
    // });
  };

  // const handleOpenClusterSeletor = () => {
  //   isShowSelector.value = true;
  // };

  // const handelClusterChange = (selected: {[key: string]: Array<RedisModel>}) => {
  //   selectedClusters.value = selected;
  //   const list = selected[ClusterTypes.REDIS];
  //   const domain = list[0].master_domain;
  //   localValue.value = domain;
  //   emits('onInputFinish', domain);
  //   window.changeConfirm = true;
  // };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });
</script>

<style lang="less" scoped>
.cluster-name-box {
  position: relative;

  // &:hover {
  //   .edit-btn {
  //     z-index: 999;
  //   }
  // }

  // .is-error {
  //   :deep(.input-error) {
  //     justify-content: center;
  //   }
  // }


  .edit-btn{
    position: absolute;
    top: 0;
    right: 5px;
    z-index: -1;
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
        color: #979BA5;
      }

      &:hover {
        background: #F0F1F5;

        .select-icon {
          color: #3A84FF;
        }

      }
    }
  }
}
</style>
