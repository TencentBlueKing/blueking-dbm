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
    class="render-target-box"
    :class="{
      'is-repeat': isRepeat
    }">
    <TableEditInput
      ref="inputRef"
      v-model="localIpText"
      :disabled="!Boolean(source)"
      :placeholder="t('请输入IP，多个英文逗号分隔')"
      :rules="rules"
      textarea />
    <div
      v-if="isRepeat"
      class="repeat-flag">
      {{ $t('重复') }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    source?: IDataRow['source'],
    modelValue: IDataRow['target'],
  }

  interface Exposes {
    getValue: () => Promise<{ [target: string]: string }>
  }

  const props = defineProps<Props>();

  const splitReg = /[\n ,，;；]/;

  const { t } = useI18n();

  const inputRef = ref();
  const localIpText = ref('');
  const isRepeat = ref(false);


  const rules = [
    {
      validator: (value: string) => {
        const ipList = _.filter(value.split(splitReg), item => _.trim(item)) as Array<string>;
        return ipList.length > 0;
      },
      message: t('IP 不能为空'),
    },
    {
      validator: (value: string) => {
        const ipList = value.split(splitReg) as Array<string>;
        return _.every(ipList, item => ipv4.test(_.trim(item)));
      },
      message: t('IP格式不正确'),
    },
    {
      validator: (value: string) => {
        const hostList = value.split(splitReg).filter(item => !!_.trim(item));
        if (_.uniq(hostList).length !== hostList.length) {
          isRepeat.value = true;
          return false;
        }
        isRepeat.value = false;
        return true;
      },
      message: t('输入的IP重复'),
    },
  ];

  // 同步外部主从机器
  watch(() => props.modelValue, () => {
    localIpText.value = props.modelValue.join(';');
  }, {
    immediate: true,
  });


  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          target: localIpText.value.split(splitReg).join('\n'),
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-target-box {
    position: relative;

    &.is-repeat {
      .input-error {
        display: none;
      }
    }

    .repeat-flag,
    .conflict-flag {
      position: absolute;
      top: 50%;
      right: 0;
      display: flex;
      height: 20px;
      padding: 0 5px;
      font-size: 12px;
      line-height: 20px;
      color: #fff;
      background-color: #ea3636;
      border-radius: 2px;
      align-self: center;
      transform: scale(0.8) translateY(-50%);
    }
  }

  .master-slave-clone-conflict-host-popover {
    padding: 9px 7px;

    .popover-header {
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: bold;
      line-height: 16px;
      color: #313238;
    }

    .popover-content {
      max-height: 300px;
      overflow: auto;
    }

    .popover-host-item {
      padding: 2px 20px 2px 0;

      &:nth-child(n+2) {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
