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
    class="redis-list-extract-keys-slider"
    :is-show="isShow"
    render-directive="if"
    :width="960"
    @closed="handleClose">
    <template #header>
      <div class="extract-keys-header">
        <template v-if="isBatch">
          <span class="extract-keys-header__title">{{ t('批量提取Key') }}</span>
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
          <span class="extract-keys-header__title">{{ t('提取Key') }}</span>
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
            <span class="extract-keys__tips-label">{{ t('可使用通配符进行提取_如_Key或Key') }}</span>
            <span class="extract-keys__tips-value">{{ t('提取以Key开头的key_包括Key') }}</span>
          </div>
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">*Key$ :</span>
            <span class="extract-keys__tips-value">{{ t('提取以Key结尾的key_包括Key') }}</span>
          </div>
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">^Key$ :</span>
            <span class="extract-keys__tips-value">{{ t('提取精确匹配的Key') }}</span>
          </div>
          <div class="extract-keys__tips-item">
            <span class="extract-keys__tips-label">* :</span>
            <span class="extract-keys__tips-value">{{ t('提取所有key') }}</span>
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
          :data="state.formdata"
          :show-overflow="false" />
      </DbForm>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { createTicket } from '@services/source/ticket';

  import { useBeforeClose, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import { generateId } from '@utils';

  import BatchEditKeys from '../RedisBatchEditKeys.vue';

  interface ExtractItem extends RedisModel {
    black_regex: string;
    white_regex: string;
  }

  interface Props {
    data?: RedisModel[];
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const formRef = ref();

  const globalBizsStore = useGlobalBizs();
  const handleBeforeClose = useBeforeClose();
  // 判断是否为批量操作
  const isBatch = computed(() => props.data.length > 1);
  // 第一个集群的数据
  const firstData = computed(() => props.data[0]);
  const keyRegexRules = [
    {
      message: t('请输入正则表达式'),
      trigger: 'blur',
      validator: (value: string) => !!value,
    },
  ];
  const columns = [
    {
      field: 'name',
      label: t('集群'),
      minWidth: 280,
      render: ({ data }: { data: ExtractItem }) => (
        <div
          v-overflow-tips={{
            allowHTML: true,
            content: `
            <p>${t('域名')}：${data.master_domain}</p>
            ${data.cluster_alias ? `<p>${'集群别名'}：${data.cluster_alias}</p>` : null}
          `,
          }}
          class='cluster-name text-overflow'>
          <span>{data.master_domain}</span>
          <br />
          <span class='cluster-name__alias'>{data.cluster_alias}</span>
        </div>
      ),
      showOverflow: false,
    },
    {
      field: 'white_regex',
      label: () => (
        <span class='key-table-header'>
          {t('包含Key')}
          <span
            class='pl-4'
            style='color: #ea3636;'>
            *
          </span>
          {isBatch.value ? (
            <BatchEditKeys
              title={t('批量设置包含Key')}
              onChange={(value: string) => handleBatchChange(value, 'white_regex')}
            />
          ) : (
            ''
          )}
        </span>
      ),
      minWidth: 280,
      render: ({ data, index }: { data: ExtractItem; index: number }) => (
        <bk-form-item
          ref={setFormItemRefs.bind(null, 'white')}
          error-display-type='tooltips'
          label-width={0}
          property={`${index}.white_regex`}
          rules={keyRegexRules}>
          <db-textarea
            ref={setRegexRefs.bind(null, 'white')}
            v-model={data.white_regex}
            class='regex-input'
            display-height='auto'
            max-height={400}
            placeholder={t('请输入正则表达式_多个换行分割')}
            teleport-to-body={false}
          />
        </bk-form-item>
      ),
    },
    {
      field: 'black_regex',
      label: () => (
        <span class='key-table-header'>
          {t('排除Key')}
          {isBatch.value ? (
            <BatchEditKeys
              title={t('批量设置排除Key')}
              onChange={(value: string) => handleBatchChange(value, 'black_regex')}
            />
          ) : (
            ''
          )}
        </span>
      ),
      minWidth: 280,
      render: ({ data, index }: { data: ExtractItem; index: number }) => (
        <bk-form-item
          ref={setFormItemRefs.bind(null, 'black')}
          error-display-type='tooltips'
          label-width={0}
          property={`${index}.black_regex`}>
          <db-textarea
            ref={setRegexRefs.bind(null, 'black')}
            v-model={data.black_regex}
            class='regex-input'
            display-height='auto'
            max-height={400}
            placeholder={t('请输入正则表达式_多个换行分割')}
            teleport-to-body={false}
          />
        </bk-form-item>
      ),
    },
  ];
  // 实际渲染表头配置
  const rederColumns = computed(() => {
    if (isBatch.value) {
      const opertaionColumn = {
        field: 'operation',
        label: t('操作'),
        render: ({ index }: { index: number }) => (
          <bk-button
            v-bk-tooltips={t('移除')}
            disabled={state.formdata.length === 1}
            theme='primary'
            text
            onClick={() => handleRemoveItem(index)}>
            {t('删除')}
          </bk-button>
        ),
        width: 88,
      };
      return [...columns, opertaionColumn];
    }

    return columns;
  });
  const state = reactive({
    formdata: [] as ExtractItem[],
    isLoading: false,
    renderKey: generateId('EXTRACT_FORM_'),
  });
  // 设置正则 refs
  const regexRefs = reactive({
    black: [] as any[],
    white: [] as any[],
  });
  // 正则 form item refs
  const formItemRefs = reactive({
    black: [] as any[],
    white: [] as any[],
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

  watch(
    () => props.data,
    (data) => {
      state.formdata = data.map((item) =>
        Object.assign({}, item, {
          black_regex: '',
          white_regex: '',
        }),
      );
      state.renderKey = generateId('EXTRACT_FORM_');
    },
    {
      deep: true,
      immediate: true,
    },
  );

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
    state.isLoading = true;
    try {
      await formRef.value?.validate?.();
      const params = {
        bk_biz_id: globalBizsStore.currentBizId,
        details: {
          rules: state.formdata.map((item) => ({
            black_regex: item.black_regex,
            cluster_id: item.id,
            domain: item.master_domain,
            white_regex: item.white_regex,
          })),
        },
        ticket_type: TicketTypes.REDIS_KEYS_EXTRACT,
      };
      const res = await createTicket(params);
      ticketMessage(res.id);
      emits('success');
      window.changeConfirm = false;
      handleClose();
    } finally {
      state.isLoading = false;
    }
  }

  async function handleClose() {
    const result = await handleBeforeClose();
    if (!result) return;
    isShow.value = false;
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
        resize: none;

        textarea {
          height: 100%;
        }
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

<style lang="less">
  .redis-list-extract-keys-slider {
    .bk-modal-content {
      max-height: calc(100vh - 125px);
      overflow-y: auto;
    }
  }
</style>
