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
  <div
    v-if="isRender"
    class="value-tag">
    <div
      ref="rootRef"
      class="tag-value-text">
      <span>
        {{ config.label }}
      </span>
      <span style="padding-right: 4px;">
        :
      </span>
      <span>
        <template v-if="isRemoteOriginLoading">
          ...
        </template>
        <template v-else>
          {{ renderText }}
        </template>
      </span>
    </div>
    <DbIcon
      class="remove-btn"
      type="close"
      @click="handleRemove" />
    <div style="display: none;">
      <div
        ref="popRef"
        style="width: 368px; padding: 9px 15px;">
        <ComFactory
          ref="inputRef"
          :model="localModel"
          :name="name"
          simple
          style="display: block"
          @cancel="handleCancel"
          @change="handleChange"
          @submit="handleSubmit" />
        <div style="margin-top: 8px; font-size: 14px; line-height: 22px; color: #3a84ff; text-align: right;">
          <span
            style="margin-right: 16px; cursor: pointer;"
            @click="handleSubmit">
            {{ t('确定') }}
          </span>
          <span
            style="cursor: pointer;"
            @click="handleCancel">
            {{ t('取消') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
  let singleIns: Instance;
  export default {

  };
</script>
<script setup lang="ts">
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    computed,
    onBeforeUnmount,
    onMounted,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ComFactory from '../com-factory/Index.vue';
  import fieldConfig from '../field-config';
  import { isValueEmpty } from '../utils';

  interface Props {
    name: string;
    value: any,
    model: Record<string, any>
  }

  interface Emits {
    (e: 'remove', name: string): void
    (e: 'change', name: string, value: any): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const config = fieldConfig[props.name];

  const rootRef = ref();
  const popRef = ref();
  const inputRef = ref();
  const localModel = shallowRef({});
  const isRemoteOriginLoading = ref(false);
  const remoteOriginalList = shallowRef<Array<any>>([]);

  const isRender = computed(() => !isValueEmpty(props.value));

  const renderText = computed(() => {
    if (isValueEmpty(props.value)) {
      return '--';
    }
    if (['cpu', 'mem', 'disk'].includes(props.name)) {
      const [min, max] = props.value;
      return `${min} 至 ${max}`;
    }

    if (props.name === 'agent_status') {
      return props.value === 0 ? '异常' : '正常';
    }

    const valueList = Array.isArray(props.value) ? props.value : [props.value];

    if (config.service && config.getNameByKey && remoteOriginalList.value.length > 0) {
      const valueNameStask: string[] = [];
      for (let i = 0; i < remoteOriginalList.value.length; i++) {
        valueList.forEach((valueItem) => {
          if (!config.getNameByKey) {
            return;
          }
          const renderName = config.getNameByKey(valueItem, remoteOriginalList.value[i]);
          if (renderName) {
            valueNameStask.push(renderName);
          }
        });
      }
      return valueNameStask.join(',');
    }

    return valueList.join(', ');
  });

  watch(() => props.model, () => {
    localModel.value = { ...props.model };
  }, {
    immediate: true,
  });

  if (config.service) {
    isRemoteOriginLoading.value = true;
    config.service()
      .then((data) => {
        remoteOriginalList.value = data;
        console.log('remoteOriginalList = ', data);
      })
      .finally(() => {
        isRemoteOriginLoading.value = false;
      });
  }

  let valueMemo: any;
  let tippyIns: Instance;

  const handleRemove = () => {
    emits('remove', props.name);
  };

  // 编辑值
  const handleChange = (fieldName: string, fieldValue: any) => {
    valueMemo = fieldValue;
    localModel.value = {
      ...localModel.value,
      [fieldName]: fieldValue,
    };
  };

  // 提交编辑状态
  const handleSubmit = () => {
    inputRef.value.getValue()
      .then(() => {
        if (valueMemo !== undefined) {
          emits('change', props.name, valueMemo);
        }
        tippyIns.hide();
      });
  };

  // 取消
  const handleCancel = () => {
    tippyIns.hide();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom-start',
      appendTo: () => document.body,
      theme: 'search-value-edit-theme light',
      maxWidth: 'none',
      trigger: 'click',
      interactive: true,
      arrow: true,
      offset: [0, 8],
      zIndex: 999,
      hideOnClick: false,
      onShow() {
        if (singleIns) {
          singleIns.hide();
        }
        singleIns = tippyIns;
      },
    });
  });

  onBeforeUnmount(() => {
    tippyIns.hide();
    tippyIns.unmount();
    tippyIns.destroy();
  });

</script>
<style lang="less" scoped>
  .value-tag {
    display: flex;
    height: 22px;
    padding: 0 6px;
    font-size: 12px;
    line-height: 22px;
    color: #63656e;
    background: #f0f1f5;
    border-radius: 2px;
    align-items: center;

    &:hover {
      background: #dcdee5;
    }

    & ~ .value-tag {
      margin-left: 6px;
    }

    .tag-value-text{
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
    }

    .remove-btn {
      padding-top: 2px;
      padding-left: 4px;
      font-size: 16px;
      cursor: pointer;
    }
  }
</style>
