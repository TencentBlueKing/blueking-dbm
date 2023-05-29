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
      :placeholder="t('请输入IP（单个）')"
      :rules="rules"
      @submit="handleInputFinish" />
  </div>
</template>
<script lang="ts">
  const hostsMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkMongoInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  interface Props {
    data?: string;
  }

  interface Emits {
    (e: 'inputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
  });
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const localValue = ref(props.data);
  const editRef = ref();

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
        const result = await checkMongoInstances({
          bizId: currentBizId,
          instance_addresses: [value],
        });
        return result.length > 0;
      },
      message: t('目标主机不存在'),
    },
    {
      validator: () => {
        const currentHostSelectMap = hostsMemo[instanceKey];
        const otheHostMemoMap = { ...hostsMemo };
        delete otheHostMemoMap[instanceKey];

        const otherHostMap = Object.values(otheHostMemoMap).reduce((result, item) => ({
          ...result,
          ...item,
        }), {} as Record<string, boolean>);
        const currentSelectHostList = Object.keys(currentHostSelectMap);
        for (let i = 0; i < currentSelectHostList.length; i++) {
          if (otherHostMap[currentSelectHostList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('目标主机重复'),
    },
  ];

  const instanceKey = `render_host_${random()}`;
  hostsMemo[instanceKey] = {};

  watch(
    () => props.data,
    (data) => {
      localValue.value = data;
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    hostsMemo[instanceKey][localValue.value] = true;
    emits('inputFinish', value);
  };

  onBeforeUnmount(() => {
    hostsMemo[instanceKey] = {};
  })

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;

    .edit-btn {
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
