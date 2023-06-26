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
      <div class="backup-header">
        <template v-if="isBatch">
          <span class="backup-header__title">{{ $t('批量备份集群') }}</span>
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
          <span class="backup-header__title">{{ $t('备份集群') }}</span>
          <template v-if="firstData">
            <span class="backup-header__title"> - {{ firstData.master_domain }}</span>
            <span
              v-if="firstData.cluster_alias"
              class="backup-header__desc">
              （{{ firstData.cluster_alias }}）
            </span>
          </template>
        </template>
      </div>
    </template>
    <div class="backup">
      <DbForm
        :key="state.renderKey"
        ref="formRef"
        class="backup__content"
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

  import BatchEdit from './BatchEdit.vue';

  import type { TableColumnRender } from '@/types/bkui-vue';

  interface DataItem extends ResourceRedisItem {
    target: string,
    backup_type: string
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
  const backupList = [{
    id: 'normal_backup',
    label: t('常规备份'),
  }, {
    id: 'forever_backup',
    label: t('长期备份'),
  }];
  const rules = [{
    trigger: 'blur',
    message: t('请选择'),
    validator: (value: string) => !!value,
  }];
  const columns = [{
    label: t('域名'),
    field: 'name',
    showOverflowTooltip: false,
    render: ({ data }: { data: DataItem }) => (
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
    label: t('架构版本'),
    field: 'cluster_type_name',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: () => (
      <span class="key-table-header">
        {t('备份目标')}
        {
          isBatch.value
            ? (
              <BatchEdit
                title={t('批量选择备份目标')}
                width={420}
                validator={validatorBatchSelect.bind(null, t('请选择备份目标'))}
                onChange={handleBatchChange.bind(null, 'target')}>
                {{
                  default: ({ state }: any) => (
                    <bk-select
                      v-model={state.value}
                      clearable={false}
                      popover-options={{ boundary: 'parent', disableTeleport: true }}>
                      { ['master', 'slave'].map(item => <bk-option value={item} label={item} />) }
                    </bk-select>
                  ),
                }}
              </BatchEdit>
            ) : ''
        }
      </span>
    ),
    field: 'target',
    render: ({ data, index }: { data: DataItem, index: number }) => (
      <bk-form-item error-display-type="tooltips" property={`${index}.target`} rules={rules} label-width={0}>
        <bk-select v-model={data.target} clearable={false}>
          { ['master', 'slave'].map(item => <bk-option value={item} label={item} />) }
        </bk-select>
      </bk-form-item>
    ),
  }, {
    label: () => (
      <span class="key-table-header">
        {t('备份类型')}
        {
          isBatch.value
            ? (
              <BatchEdit
                title={t('批量选择备份类型')}
                width={420}
                validator={validatorBatchSelect.bind(null, t('请选择备份类型'))}
                onChange={handleBatchChange.bind(null, 'backup_type')}>
                {{
                  default: ({ state }: any) => (
                    <bk-select
                      v-model={state.value}
                      clearable={false}
                      popover-options={{ boundary: 'parent', disableTeleport: true }}>
                      { backupList.map(item => <bk-option value={item.id} label={item.label} />) }
                    </bk-select>
                  ),
                }}
              </BatchEdit>
            ) : ''
        }
      </span>
    ),
    field: 'backup_type',
    render: ({ data, index }: { data: DataItem, index: number }) => (
      <bk-form-item error-display-type="tooltips" property={`${index}.backup_type`} rules={rules} label-width={0}>
        <bk-select v-model={data.backup_type} clearable={false}>
          { backupList.map(item => <bk-option value={item.id} label={item.label} />) }
        </bk-select>
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
            {t('删除')}
          </bk-button>
        ),
      };
      return [...columns, opertaionColumn];
    }

    return columns;
  });
  const state = reactive({
    isLoading: false,
    formdata: [] as DataItem[],
    renderKey: generateId('BACKUP_FORM_'),
  });

  watch(() => props.data, (data) => {
    state.formdata = data.map(item => ({
      backup_type: '',
      target: '',
      ...item,
    }));
    state.renderKey = generateId('BACKUP_FORM_');
  }, { immediate: true, deep: true });

  function handleRemoveItem(index: number) {
    state.formdata.splice(index, 1);
  }

  function validatorBatchSelect(errorText: string, value: string) {
    return {
      isPass: !!value,
      errorText,
    };
  }

  function handleBatchChange(key: 'backup_type' | 'target', value: string) {
    state.formdata.forEach((item) => {
      // eslint-disable-next-line no-param-reassign
      item[key] = value;
    });
  }

  async function handleSubmit() {
    await formRef.value?.validate?.();

    state.isLoading = true;
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      ticket_type: TicketTypes.REDIS_BACKUP,
      details: {
        rules: state.formdata.map(item => ({
          cluster_id: item.id,
          domain: item.master_domain,
          target: item.target,
          backup_type: item.backup_type,
        })),
      },
    };
    return createTicket(params)
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
  }
</script>

<style lang="less" scoped>
  .backup {
    padding: 24px 40px;

    &__content {
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

  .backup-header {
    &__desc {
      font-size: @font-size-mini;
      color: @gray-color;

      strong {
        color: @success-color;
      }
    }
  }
</style>
