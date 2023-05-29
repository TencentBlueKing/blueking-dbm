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
  <BkSideslider
    :before-close="handleBeforeClose"
    :is-show="isShow"
    :width="960"
    @closed="handleClose">
    <template #header>
      <div class="extract-keys-header">
        <template v-if="isBatch">
          <span class="extract-keys-header__title">{{ $t('批量提取Key') }}</span>
          （
          <I18nT
            class="purge-header__desc"
            keypath="已选n个集群"
            tag="span">
            <strong>{{ state.formdata.length }}</strong>
          </I18nT>
          ）
        </template>
        <template v-else>
          <span class="extract-keys-header__title">{{ $t('提取Key') }}</span>
          <template v-if="firstData">
            <span class="extract-keys-header__title"> - {{ firstData.master_domain }}</span>
            <span
              v-if="firstData.cluster_alias"
              class="extract-keys-header__desc">
              （{{ firstData.cluster_alias }}）
            </span>
          </template>
        </template>
      </div>
    </template>
    <div class="extract-keys">
      <BkAlert closable>
        <div class="extract-keys__tips">
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">{{ $t('可使用通配符进行提取_如_Key或Key') }}</span>
            <span class="extract-keys__tips-value">{{ $t('提取以Key开头的key_包括Key') }}</span>
          </div>
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">*Key$ :</span>
            <span class="extract-keys__tips-value">{{ $t('提取以Key结尾的key_包括Key') }}</span>
          </div>
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">^Key$ :</span>
            <span class="extract-keys__tips-value">{{ $t('提取精确匹配的Key') }}</span>
          </div>
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">* :</span>
            <span class="extract-keys__tips-value">{{ $t('提取所有key') }}</span>
          </div>
        </div>
      </BkAlert>
      <DbForm
        :key="state.renderKey"
        ref="formRef"
        class="extract-keys__content"
        :model="state.formdata">
        <DbOriginalTable
          class="custom-edit-table"
          :columns="rederColumns"
          :data="state.formdata" />
      </DbForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/ticket';
  import type { ResourceRedisItem } from '@services/types/clusters';

  import { useBeforeClose, useStickyFooter, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import { generateId } from '@utils';

  import BatchEditKeys from './BatchEditKeys.vue';

  interface ExtractItem extends ResourceRedisItem {
    white_regex: string,
    black_regex: string
  }

  const props = defineProps({
    isShow: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Array as PropType<ResourceRedisItem[]>,
      default: () => ([]),
    },
  });

  const emits = defineEmits(['update:is-show', 'success']);

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const formRef = ref();
  /** 设置底部按钮粘性布局 */
  useStickyFooter(formRef);

  const globalBizsStore = useGlobalBizs();
  const handleBeforeClose = useBeforeClose();
  // 判断是否为批量操作
  const isBatch = computed(() => props.data.length > 1);
  // 第一个集群的数据
  const firstData = computed(() => props.data[0]);
  const keyRegexRules = [{
    trigger: 'blur',
    message: t('请输入正则表达式'),
    validator: (value: string) => !!value,
  }];
  const columns = [{
    label: t('集群'),
    field: 'name',
    showOverflowTooltip: false,
    render: ({ data }: { data: ExtractItem }) => (
      <div
        class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.master_domain}</p>
            ${data.cluster_alias ? `<p>${('集群别名')}：${data.cluster_alias}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.master_domain}</span><br />
        <span class="cluster-name__alias">{data.cluster_alias}</span>
      </div>
    ),
  }, {
    label: () => (
      <span class="key-table-header">
        { t('包含Key') }
        <span style="color: #ea3636;" class="pl-4">*</span>
        {
          isBatch.value
            ? (
              <BatchEditKeys
                title={t('批量设置包含Key')}
                onChange={(value: string) => handleBatchChange(value, 'white_regex')} />
            ) : ''
        }
      </span>
    ),
    field: 'white_regex',
    render: ({ data, index }: { data: ExtractItem, index: number }) => (
      <bk-form-item
        error-display-type="tooltips"
        ref={setFormItemRefs.bind(null, 'white')}
        property={`${index}.white_regex`}
        rules={keyRegexRules}
        label-width={0}>
        <db-textarea
          ref={setRegexRefs.bind(null, 'white')}
          class="regex-input"
          placeholder={t('请输入正则表达式_多个换行分割')}
          display-height="auto"
          v-model={data.white_regex}
          max-height={100}
          teleport-to-body={false} />
      </bk-form-item>
    ),
  }, {
    label: () => (
      <span class="key-table-header">
        { t('排除Key') }
        {
          isBatch.value
            ? (
              <BatchEditKeys
                title={t('批量设置排除Key')}
                onChange={(value: string) => handleBatchChange(value, 'black_regex')} />
            ) : ''
        }
      </span>
    ),
    field: 'black_regex',
    render: ({ data, index }: { data: ExtractItem, index: number }) => (
      <bk-form-item
        error-display-type="tooltips"
        ref={setFormItemRefs.bind(null, 'black')}
        property={`${index}.black_regex`}
        label-width={0}>
        <db-textarea
          ref={setRegexRefs.bind(null, 'black')}
          class="regex-input"
          placeholder={t('请输入正则表达式_多个换行分割')}
          display-height="auto"
          v-model={data.black_regex}
          max-height={100}
          teleport-to-body={false} />
      </bk-form-item>
    ),
  }];
  // 实际渲染表头配置
  const rederColumns = computed(() => {
    if (isBatch.value) {
      const opertaionColumn = {
        label: t('操作'),
        field: 'operation',
        width: 88,
        render: ({ index }: { index: number }) => (
          <bk-button
            theme="primary"
            text
            v-bk-tooltips={t('移除')}
            disabled={state.formdata.length === 1}
            onClick={() => handleRemoveItem(index)}>
            { t('删除') }
          </bk-button>
        ),
      };
      return [...columns, opertaionColumn];
    }

    return columns;
  });
  const state = reactive({
    isLoading: false,
    formdata: [] as ExtractItem[],
    renderKey: generateId('EXTRACT_FORM_'),
  });
  // 设置正则 refs
  const regexRefs = reactive({
    white: [] as any[],
    black: [] as any[],
  });
  // 正则 form item refs
  const formItemRefs = reactive({
    white: [] as any[],
    black: [] as any[],
  });

  /**
   * 存 textarea ref
   */
  function setRegexRefs(key: 'white' | 'black', el: Element) {
    if (el && key) {
      regexRefs[key].push(el);
    }
  }

  /**
   * 存 form item refs
   */
  function setFormItemRefs(key: 'white' | 'black', el: Element) {
    if (el && key) {
      formItemRefs[key].push(el);
    }
  }

  watch(() => props.data, (data) => {
    state.formdata = data.map(item => ({
      white_regex: '',
      black_regex: '',
      ...item,
    }));
    state.renderKey = generateId('EXTRACT_FORM_');
  }, { immediate: true, deep: true });

  function handleRemoveItem(index: number) {
    state.formdata.splice(index, 1);
  }

  function handleBatchChange(value: string, key: 'white_regex' | 'black_regex') {
    state.formdata.forEach((item) => {
      // eslint-disable-next-line no-param-reassign
      item[key] = value;
    });
    nextTick(() => {
      // 设置 textarea height
      if (key === 'white_regex') {
        regexRefs.white.forEach((item) => {
          item?.setTextareaHeight?.();
        });
      } else {
        regexRefs.black.forEach((item) => {
          item?.setTextareaHeight?.();
        });
      }
    });
  }

  async function handleSubmit() {
    await formRef.value?.validate?.();

    state.isLoading = true;
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      ticket_type: TicketTypes.REDIS_KEYS_EXTRACT,
      details: {
        rules: state.formdata.map(item => ({
          cluster_id: item.id,
          domain: item.master_domain,
          white_regex: item.white_regex,
          black_regex: item.black_regex,
        })),
      },
    };
    createTicket(params)
      .then((res) => {
        ticketMessage(res.id);
        nextTick(() => {
          emits('success');
          window.changeConfirm = false;
          handleClose();
        });
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    emits('update:is-show', false);
    window.changeConfirm = false;
    regexRefs.white = [];
    regexRefs.black = [];
  }
</script>

<style lang="less" scoped>
  .extract-keys {
    padding: 24px 40px;

    .bk-alert {
      :deep(.bk-alert-icon-info) {
        align-self: flex-start;
      }
    }

    &__tips {
      &-item {
        display: flex;
        padding-bottom: 4px;
        font-size: @font-size-mini;

        &:last-child {
          padding-bottom: 0;
        }
      }

      &-label {
        width: 236px;
        padding-right: 8px;
        text-align: right;
        flex-shrink: 0;
      }

      &-value {
        word-break: break-all;
      }
    }

    &__content {
      padding-top: 12px;

      :deep(.cluster-name) {
        padding: 8px 0;
        line-height: 16px;

        &__alias {
          color: @light-gray;
        }
      }

      :deep(.bk-form-label) {
        display: none;
      }

      :deep(.bk-form-error-tips) {
        top: 50%;
        transform: translateY(-50%);
      }

      :deep(.regex-input) {
        margin: 8px 0;
      }
    }
  }

  .extract-keys-header {
    &__desc {
      font-size: @font-size-mini;
      color: @gray-color;

      strong {
        color: @success-color;
      }
    }
  }
</style>
