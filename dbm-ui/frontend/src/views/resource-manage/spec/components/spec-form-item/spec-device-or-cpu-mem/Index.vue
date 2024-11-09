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
  <div class="spec-device-or-mem spec-form-item">
    <div class="spec-form-item-label device-or-mem-label">
      <BkSelect
        v-model="currentType"
        :disabled="isEdit"
        :filterable="false"
        @change="handleChooseType"
        @toggle="handleTogglePopover">
        <template #trigger>
          <div
            v-bk-tooltips="{
              content: t('不支持修改'),
              disabled: !isEdit,
            }"
            class="operation-more-main">
            <span class="label-content">
              <BkButton
                class="mr-4"
                text>
                {{ currentTitle }}
              </BkButton>
              <DbIcon
                class="more-icon"
                :class="{
                  'more-icon-active': isRotate,
                  'icon-disabled': isEdit,
                }"
                type="down-shape" />
            </span>
          </div>
        </template>
        <BkOption
          v-for="(item, index) in titleList"
          :id="item.value"
          :key="index"
          :name="item.title" />
      </BkSelect>
    </div>
    <SpecDevice
      v-if="currentType === 'device_class'"
      v-model="deviceClassModelValue"
      :is-edit="isEdit" />
    <div
      v-else
      class="cpu-mem-main">
      <SpecCPU
        v-model="cpuModelValue"
        :is-edit="isEdit" />
      <SpecMem
        v-model="memModelValue"
        :is-edit="isEdit" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import SpecCPU from './components/SpecCPU.vue';
  import SpecDevice from './components/SpecDevice.vue';
  import SpecMem from './components/SpecMem.vue';

  interface Props {
    isEdit: boolean;
  }

  interface Exposes {
    getCurrentType: () => string;
  }

  withDefaults(defineProps<Props>(), {
    isEdit: false,
  });

  const deviceClassModelValue = defineModel<string[]>('deviceClass', { required: true });

  const cpuModelValue = defineModel<{
    min: number | string;
    max: number | string;
  }>('cpu', { required: true });

  const memModelValue = defineModel<{
    min: number | string;
    max: number | string;
  }>('mem', { required: true });

  const { t } = useI18n();

  const titleList = [
    {
      title: t('机型'),
      value: 'device_class',
    },
    {
      title: t('CPU/内存'),
      value: 'cpu_mem',
    },
  ];

  const isRotate = ref(false);
  const currentType = ref(titleList[0].value);

  const currentTitle = computed(() => (currentType.value === 'device_class' ? titleList[0].title : titleList[1].title));

  const handleTogglePopover = (isShow: boolean) => {
    isRotate.value = isShow;
  };

  const handleChooseType = (type: string) => {
    if (type === 'device_class') {
      cpuModelValue.value = {
        min: 0,
        max: 0,
      };
      memModelValue.value = {
        min: 0,
        max: 0,
      };
    } else {
      deviceClassModelValue.value = [];
    }

    if (currentType.value === type) {
      return;
    }

    currentType.value = type;
  };

  onMounted(() => {
    if (deviceClassModelValue.value.length > 0 || (!deviceClassModelValue.value.length && !cpuModelValue.value.max)) {
      // 优先展示机型
      currentType.value = titleList[0].value;
      return;
    }

    currentType.value = titleList[1].value;
  });

  defineExpose<Exposes>({
    getCurrentType() {
      return currentType.value;
    },
  });
</script>

<style lang="less" scoped>
  @import '../specFormItem.less';

  .spec-device-or-mem {
    .device-or-mem-label {
      &::after {
        display: none;
      }
    }
  }

  .operation-more-main {
    display: flex;
    color: #63656e;
    cursor: pointer;
    align-items: center;

    .label-content {
      position: relative;

      &::after {
        position: absolute;
        top: 1px;
        right: -13px;
        width: 14px;
        font-weight: normal;
        color: @danger-color;
        text-align: center;
        content: '*';
      }

      .more-icon {
        display: inline-block;
        transform: rotate(0deg);
        transition: all 0.5s;
      }

      .more-icon-active {
        transform: rotate(-180deg);
      }

      .icon-disabled {
        color: #c4c6cc;
      }
    }
  }

  .cpu-mem-main {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
</style>
