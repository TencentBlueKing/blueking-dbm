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
  <EditableColumn
    :append-rules="rules"
    :disabled-method="disabledMethod"
    field="new_readonly_host"
    :label="t('只读主机（旧 -> 新）')"
    :loading="loading"
    :min-width="400">
    <template #head>
      <div
        v-bk-tooltips="t('有顺序之分，为一一对应替换')"
        class="readonly-host-head">
        {{ t('只读主机（旧 -> 新）') }}
      </div>
      <span class="required-icon" />
    </template>
    <EditableTextarea
      ref="textareaRef"
      v-model="inputIps"
      class="readonly-host-textarea"
      :class="{
        'readonly-host-textarea--active': hostLimit > 0,
      }"
      :placeholder="
        cluster.id
          ? hostLimit
            ? t('请输入或选择 n 台 IP，按照对应顺序进行替换', { n: hostLimit })
            : t('无只读主机')
          : t('选择集群后生成')
      "
      :rows="hostLimit"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus">
      <template #prepend>
        <div
          v-for="item in readonlyHost"
          :key="item.ip">
          <div class="origin-readonly-host">
            <div class="origin-readonly-host-info">{{ item.ip }}（{{ item.bk_sub_zone || '--' }}）</div>
            <div class="origin-readonly-host-arrow">-></div>
          </div>
        </div>
      </template>
      <template #append>
        <DbIcon
          v-bk-tooltips="t('从资源池选择')"
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableTextarea>
  </EditableColumn>
  <ResourceHostSelector
    v-model="selected"
    v-model:is-show="showSelector"
    :limit="hostLimit"
    :params="{
      for_bizs: [currentBizId, 0],
      resource_types: [DBTypes.MYSQL, 'PUBLIC'],
    }"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { fetchList } from '@services/source/dbresourceResource';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { batchSplitRegex, ipv4 } from '@common/regex';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface HostInfo {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  interface Props {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    } & TendbhaModel;
  }

  const props = defineProps<Props>();

  const readonlyHost = defineModel<TendbhaModel['slaves']>('readonlyHost', {
    required: true,
  });

  const newReadonlyHost = defineModel<HostInfo[]>('newReadonlyHost', {
    required: true,
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const inputIps = ref('');
  const textareaRef = ref();
  const hostMemo = ref<Record<string, boolean>>({});
  const showSelector = ref(false);

  const hostLimit = computed(() => readonlyHost.value.length);
  const selected = computed(() =>
    newReadonlyHost.value.filter((item) => !!item.ip).length ? (newReadonlyHost.value as IValue[]) : ([] as IValue[]),
  );

  // 格式化输入转为ips: string[]
  const formatInputToIps = (value: string) => {
    return value
      .trim()
      .replace(/（[^）]*）/g, '')
      .split(batchSplitRegex);
  };

  const rules = [
    {
      message: t('新只读主机数与旧只读主机数不一致'),
      trigger: 'blur',
      validator: () => {
        if (!inputIps.value) {
          return true;
        }
        const ips = formatInputToIps(inputIps.value);
        return ips.length === hostLimit.value;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: () => {
        if (!inputIps.value) {
          return true;
        }
        const formatErrors = formatInputToIps(inputIps.value).filter((item) => !ipv4.test(item));
        return formatErrors.length ? t('IP格式有误，请输入合法IP: xx', [formatErrors.join('、')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: () => {
        if (!inputIps.value) {
          return true;
        }
        const ips = formatInputToIps(inputIps.value);
        const notExist: string[] = [];
        ips.forEach((item) => {
          if (!hostMemo.value[item]) {
            notExist.push(item);
          }
        });
        return notExist.length ? t('主机不存在: xx', [notExist.join('、')]) : true;
      },
    },
  ];

  const { loading, run: queryHost } = useRequest(fetchList, {
    manual: true,
    onSuccess: (data) => {
      handleSelectorChange(data.results);
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    if (readonlyHost.value.length === 0) {
      return t('无只读主机');
    }
    return '';
  };

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  // 聚焦时，生成对应行数
  const handleFocus = () => {
    if (inputIps.value) {
      // 删除括号及其中的内容
      inputIps.value = formatInputToIps(inputIps.value).join('\n');
      return;
    }
    for (let i = 0; i < hostLimit.value - 1; i++) {
      inputIps.value += '\n';
    }
  };

  // 失焦查询ip信息
  const handleBlur = () => {
    handleChange(inputIps.value);
  };

  const handleChange = (value: string) => {
    newReadonlyHost.value = [];
    const ips = value.split(batchSplitRegex).filter((item) => ipv4.test(item.trim()));
    if (ips.length === hostLimit.value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        hosts: ips.join(','),
        limit: hostLimit.value,
        offset: 0,
      });
    }
  };

  const handleSelectorChange = (hostList: IValue[]) => {
    if (hostList.length) {
      inputIps.value = hostList.map((item) => `${item.ip}（${item.sub_zone || '--'}）`).join('\n');
      newReadonlyHost.value = hostList.map((item) => ({
        bk_biz_id: item.dedicated_biz || item.bk_biz_id,
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        bk_sub_zone: item.sub_zone,
        ip: item.ip,
      }));
      hostMemo.value = hostList.reduce<Record<string, boolean>>((acc, cur) => {
        Object.assign(acc, {
          [cur.ip]: true,
        });
        return acc;
      }, {});
    }
  };

  // 限制行数的处理函数
  const limitTextareaRows = (text: string): string => {
    const lines = text.split('\n');
    const maxRows = hostLimit.value;

    if (lines.length > maxRows) {
      return lines.slice(0, maxRows).join('\n');
    }
    return text;
  };

  // 监听键盘事件，拦截换行操作
  const handleKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      const textarea = event.target as HTMLTextAreaElement;
      const currentLines = textarea.value.split('\n');
      const maxRows = hostLimit.value;

      if (currentLines.length >= maxRows) {
        event.preventDefault();
      }
    }
  };

  // 监听粘贴事件，截取对应行数内容
  const handlePaste = (event: ClipboardEvent) => {
    event.preventDefault();

    const clipboardData = event.clipboardData?.getData('text') || '';
    const textarea = event.target as HTMLTextAreaElement;
    const cursorPosition = textarea.selectionStart;
    const textBeforeCursor = textarea.value.substring(0, cursorPosition);
    const textAfterCursor = textarea.value.substring(textarea.selectionEnd);

    // 合并文本
    const newText = textBeforeCursor + clipboardData + textAfterCursor;
    // 限制行数
    const limitedText = limitTextareaRows(newText);
    // 更新输入框内容
    inputIps.value = limitedText;

    // 触发 change 事件
    nextTick(() => {
      handleChange(limitedText);
    });
  };

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        readonlyHost.value =
          _.sortBy(
            props.cluster.slaves?.filter((item) => !item.is_stand_by), // is_stand_by === false 为原只读主机
            (item) => item.bk_host_id,
          ) || [];

        setTimeout(() => {
          // 单据克隆回显
          if (newReadonlyHost.value.length > 0) {
            handleChange(newReadonlyHost.value.map((item) => item.ip).join('\n'));
          }
        }, 60);
      }
    },
  );

  // 组件挂载后添加事件监听
  onMounted(() => {
    setTimeout(() => {
      const textareaElement = textareaRef.value?.$el?.querySelector('textarea');
      if (textareaElement) {
        textareaElement.addEventListener('keydown', handleKeydown);
        textareaElement.addEventListener('paste', handlePaste);
      }
    }, 60);
  });

  // 组件卸载前移除事件监听
  onBeforeUnmount(() => {
    const textareaElement = textareaRef.value?.$el?.querySelector('textarea');
    if (textareaElement) {
      textareaElement.removeEventListener('keydown', handleKeydown);
      textareaElement.removeEventListener('paste', handlePaste);
    }
  });
</script>
<style lang="less">
  .readonly-host-textarea {
    .bk-editable-textarea-prepend-wrapper {
      padding-left: 0;
      display: initial;
      user-select: text;
    }

    textarea {
      padding: 0;
    }
  }

  .readonly-host-textarea--active {
    textarea {
      height: 100% !important;
      min-height: initial !important;
      line-height: 28px !important;
    }

    .bk-textarea--clear-icon {
      top: 50% !important;
      transform: translateY(-50%) !important;
    }
  }
</style>
<style lang="less" scoped>
  .select-icon {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }

  .readonly-host-head {
    border-bottom: 1px dashed #979ba5;
  }

  .required-icon::after {
    line-height: 20px;
    color: #ea3636;
    content: '*';
  }

  .origin-readonly-host {
    display: flex;
    line-height: 28px;
    justify-content: end;

    .origin-readonly-host-info {
      margin: 0 0 0 8px;
      white-space: nowrap;
      text-align: end;
      font-size: 12px;
      padding: 0 8px;
      color: #979ba5;
      background: #fafbfd;
    }

    .origin-readonly-host-arrow {
      width: 15px;
    }
  }
</style>
