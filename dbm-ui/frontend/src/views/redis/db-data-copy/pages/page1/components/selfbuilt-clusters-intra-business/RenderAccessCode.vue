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
    class="table-edit-input"
    :class="{'is-error': Boolean(errorMessage)}">
    <BkInput
      v-model="localValue"
      class="input-box"
      :placeholder="t('请输入连接密码')"
      type="password"
      @blur="handleBlur"
      @input="handleInput"
      @keydown="handleKeydown"
      @paste="handlePaste" />
    <div
      v-if="errorMessage"
      class="input-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  // TODO INTERFACE
  import { testRedisConnection } from '@services/redis/toolbox';

  import useValidtor from '@views/redis/common/edit/hooks/useValidtor';

  import { encodeMult } from '@utils';

  interface Props {
    srcCluster: string;
    dstCluster: string;
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const localValue = ref('');

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('密码不能为空'),
    },
    {
      validator: () => Boolean(props.srcCluster),
      message: t('请先输入源集群'),
    },
    {
      validator: () => Boolean(props.dstCluster),
      message: t('请先选择目标集群'),
    },
    {
      validator: async (value: string) => {
        const r = await testRedisConnection({
          data_copy_type: 'user_built_to_dbm',
          infos: [{
            src_cluster: props.srcCluster,
            src_cluster_password: value,
            dst_cluster: props.dstCluster,
            dst_cluster_password: '',
          }],
        });
        return r;
      },
      message: t('密码不匹配'),
    },
  ];

  const {
    message: errorMessage,
    validator,
  } = useValidtor(rules);

  // 响应输入
  const handleInput = (value: string) => {
    localValue.value = value;
    window.changeConfirm = true;
  };

  // 失去焦点
  const handleBlur = (event: FocusEvent) => {
    event.preventDefault();

    validator(localValue.value)
      .then(() => {
        window.changeConfirm = true;
      });
  };

  // enter键提交
  const handleKeydown = (value: string, event: KeyboardEvent) => {
    if (event.which === 13 || event.key === 'Enter') {
      event.preventDefault();
      validator(localValue.value)
        .then((result) => {
          if (result) {
            window.changeConfirm = true;
          }
        });
    }
  };

  // 粘贴
  const handlePaste = (value: string, event: ClipboardEvent) => {
    event.preventDefault();
    let paste = (event.clipboardData || window.clipboardData).getData('text');
    paste = encodeMult(paste);
    localValue.value = paste;
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
.is-error {
  background-color: #fff0f1 !important;

  :deep(input) {
    background: transparent;
  }

  :deep(.bk-input--suffix-icon) {
    display: none !important;
  }
}

.table-edit-input {
  position: relative;
  height: 42px;
  overflow: hidden;
  cursor: pointer;
  background: #fff;
  border: 1px solid transparent;

  &:hover {
    background-color: #fafbfd;
    border: 1px solid #a3c5fd;
  }

  .input-box {
    width: 100%;
    height: 100%;
    padding: 0;
    background: inherit;
    border: none;
    outline: none;

    :deep(.bk-input) {
      border-radius: 0;

      input {
        border: 1px solid transparent;
        border-radius: 0;

        &:focus {
          border-color: 1px solid #3a84ff;
        }
      }
    }

    :deep(.bk-input--number-control) {
      display: none !important;
    }


  }


  .input-error {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    display: flex;
    padding-right: 10px;
    font-size: 14px;
    color: #ea3636;
    align-items: center;
  }
}
</style>
