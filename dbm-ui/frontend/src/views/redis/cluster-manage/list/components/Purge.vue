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
      <div class="purge-header">
        <template v-if="isBatch">
          <span class="purge-header__title">{{ $t('批量清档集群') }}</span>
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
          <span class="purge-header__title">{{ $t('清档集群') }}</span>
          <template v-if="firstData">
            <span class="purge-header__title"> - {{ firstData.master_domain }}</span>
            <span
              v-if="firstData.cluster_alias"
              class="purge-header__desc">
              （{{ firstData.cluster_alias }}）
            </span>
          </template>
        </template>
      </div>
    </template>
    <div class="purge">
      <DbForm
        :key="state.renderKey"
        ref="formRef"
        class="purge__content"
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

  interface DataItem extends ResourceRedisItem {
    force: boolean,
    backup: boolean
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
  const formRef = ref();
  /** 设置底部按钮粘性布局 */
  useStickyFooter(formRef);

  const globalBizsStore = useGlobalBizs();
  const handleBeforeClose = useBeforeClose();
  const ticketMessage = useTicketMessage();

  // 判断是否为批量操作
  const isBatch = computed(() => props.data.length > 1);
  // 第一个集群的数据
  const firstData = computed(() => props.data[0]);
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
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: () => (
      <bk-checkbox
        model-value={isCheckedAllForce.value}
        false-label={false}
        onChange={(value: boolean) => handleChangeChecked('force', value)}>
        { t('强制清档') }
      </bk-checkbox>
    ),
    field: 'force',
    render: ({ data }: { data: DataItem }) => (
      <bk-checkbox v-model={data.force} false-label={false} style="vertical-align: middle;" />
    ),
  }, {
    label: () => (
      <bk-checkbox
        model-value={isCheckedAllBackup.value}
        false-label={false}
        onChange={(value: boolean) => handleChangeChecked('backup', value)}>
        { t('清档前备份') }
      </bk-checkbox>
    ),
    field: 'backup',
    render: ({ data }: { data: DataItem }) => (
      <bk-checkbox v-model={data.backup} false-label={false} style="vertical-align: middle;" />
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
    formdata: [] as DataItem[],
    renderKey: generateId('PURGE_FORM_'),
  });
  const isCheckedAllForce = computed(() => state.formdata.every(item => item.force));
  const isCheckedAllBackup = computed(() => state.formdata.every(item => item.backup));

  watch(() => props.data, (data) => {
    state.formdata = data.map(item => ({
      backup: false,
      force: false,
      ...item,
    }));
    state.renderKey = generateId('PURGE_FORM_');
  }, { immediate: true, deep: true });

  function handleRemoveItem(index: number) {
    state.formdata.splice(index, 1);
  }

  /**
   * 全选状态切换
   */
  function handleChangeChecked(type: 'force' | 'backup', value: boolean) {
    for (const item of state.formdata) {
      item[type] = value;
    }
  }

  async function handleSubmit() {
    await formRef.value?.validate?.();

    state.isLoading = true;
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
      ticket_type: TicketTypes.REDIS_PURGE,
      details: {
        rules: state.formdata.map(item => ({
          cluster_id: item.id,
          domain: item.master_domain,
          cluster_type: item.cluster_type,
          force: item.force,
          backup: item.backup,
          db_list: [],
          flushall: true, // TODO: 目前都是 true, 后续根据后端实现调整
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
  .purge {
    padding: 24px 40px;

    &__content {
      :deep(.cluster-name) {
        padding: 8px 0;
        line-height: 16px;

        &__alias {
          color: @light-gray;
        }
      }
    }
  }

  .purge-header {
    &__desc {
      font-size: @font-size-mini;
      color: @gray-color;

      strong {
        color: @success-color;
      }
    }
  }
</style>
