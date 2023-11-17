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
      :placeholder="$t('请输入IP（单个）')"
      :rules="rules"
      @submit="handleInputFinish" />
    <!-- <BkPopover
      :content="t('从业务拓扑选择')"
      placement="top"
      :popover-delay="0">
      <div
        class="edit-btn"
        @click="handleOpenSeletor">
        <div class="edit-btn-inner">
          <DbIcon
            class="select-icon"
            type="host-select" />
        </div>
      </div>
    </BkPopover> -->
  </div>
  <!-- <InstanceSelector
    v-model:is-show="isShowSelector"
    :active-tab="activeTab"
    db-type="redis"
    is-radio-mode
    :panel-list="[activeTab, 'manualInput']"
    :role="role"
    :selected="selected"
    @change="handelRadioChange" /> -->
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkRedisInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  // import InstanceSelector, {
  //   type InstanceSelectorValues,
  // } from '@views/redis/common/instance-selector/Index.vue';

  interface Props {
    // activeTab: 'idleHosts' | 'masterFailHosts' | 'createSlaveIdleHosts',
    // role: string,
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

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // const isShowSelector = ref(false);
  const localValue = ref(props.data);
  const editRef = ref();

  // const selected = shallowRef({
  //   createSlaveIdleHosts: [],
  //   masterFailHosts: [],
  //   idleHosts: [],
  // } as InstanceSelectorValues);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('IP不能为空'),
    },
    {
      validator: (value: string) => ipv4.test(value),
      message: t('IP格式不正确'),
    },
    {
      validator: async (value: string) => {
        const r = await checkRedisInstances({
          bizId: currentBizId,
          instance_addresses: [value],
        });
        return r.length > 0;
      },
      message: t('目标主机不存在'),
    },
    {
      validator: (value: string) => props.inputed.filter(item => item === value).length < 2,
      message: t('目标主机重复'),
    },
  ];

  watch(() => props.data, (data) => {
    localValue.value = data;
    // selected.value = {
    //   [props.activeTab]: [{
    //     ip: data,
    //   }],
    // } as InstanceSelectorValues;
  }, {
    immediate: true,
  });

  // const handelRadioChange = (data: InstanceSelectorValues) => {
  //   selected.value = data;
  //   const list = selected.value[props.activeTab];
  //   const domain = list[0].ip;
  //   localValue.value = domain;
  //   emits('onInputFinish', data[props.activeTab][0].ip);
  //   window.changeConfirm = true;
  // };

  // const handleOpenSeletor = () => {
  //   isShowSelector.value = true;
  // };

  const handleInputFinish = (value: string) => {
    emits('onInputFinish', value);
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
  .render-host-box {
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
