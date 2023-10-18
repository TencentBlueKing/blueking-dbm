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
  <BkDialog
    class="result-files"
    dialog-type="show"
    :is-show="isShow"
    :title="$t('查看结果文件')"
    :width="1140"
    @closed="handleClose">
    <div class="mb-24">
      <span
        v-bk-tooltips="{
          disabled: hasSelected,
          content: $t('请选择结果项')
        }"
        class="inline-block">
        <BkButton
          class="mr-8"
          :disabled="!hasSelected"
          :loading="state.isBatchDownloading"
          @click="handleDownload()">
          {{ $t('打包下载') }}
        </BkButton>
      </span>
      <span
        v-if="showDelete"
        v-bk-tooltips="{
          disabled: hasSelected,
          content: $t('请选择结果项')
        }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelected"
          @click="handleDeleteKeys()">
          {{ $t('删除Key') }}
        </BkButton>
      </span>
    </div>
    <BkLoading :loading="state.isLoading">
      <DbOriginalTable
        class="result-files__table"
        :columns="columns"
        :data="state.data"
        :height="460"
        :is-anomalies="isAnomalies"
        :row-height="56"
        @refresh="fetchKeyFiles"
        @selection-change="handleTableSelected" />
    </BkLoading>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getKeyFiles, getRedisFileUrls } from '@services/taskflow';
  import { createTicket } from '@services/ticket';
  import type { KeyFileItem } from '@services/types/taskflow';

  import { useCopy, useInfoWithIcon, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import { messageWarn } from '@utils';

  import type { TableSelectionData } from '@/types/bkui-vue';

  interface Props {
    id: string,
    showDelete?: boolean
  }

  const props = withDefaults(defineProps<Props>(), {
    showDelete: true,
  });
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const ticketMessage = useTicketMessage();

  const isAnomalies = ref(false);
  const state = reactive({
    isLoading: false,
    data: [] as KeyFileItem[],
    selected: [] as KeyFileItem[],
    downloadLoadings: [] as boolean[],
    fileLoadings: [] as boolean[],
    isBatchDownloading: false,
  });
  const columns = [{
    type: 'selection',
    width: 52,
  }, {
    label: t('目录'),
    field: 'name',
    showOverflowTooltip: true,
  }, {
    label: t('大小'),
    field: 'size_display',
    width: 100,
  }, {
    label: t('集群'),
    field: 'files',
    showOverflowTooltip: false,
    render: ({ data }: { data: KeyFileItem }) => (
      <div
        class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.domain}</p>
            ${data.cluster_alias ? `<p>${('集群别名')}：${data.cluster_alias}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.domain}</span><br />
        <span class="cluster-name__alias">{data.cluster_alias}</span>
      </div>
    ),
  }, {
    label: t('提取时间'),
    field: 'created_time',
    width: 150,
  }, {
    label: t('操作'),
    field: 'operations',
    width: 200,
    render: ({ index, data }: { index: number, data: KeyFileItem }) => (
      <div>
        <bk-button class="mr-8" text theme="primary" loading={state.downloadLoadings[index]} onClick={handleDownload.bind(null, [data], index)}>{ t('下载') }</bk-button>
        <bk-button text theme="primary" loading={state.fileLoadings[index]} onClick={getDownloadUrl.bind(null, data, index)}>{ t('复制文件地址') }</bk-button>
      </div>
    ),
  }];
  const hasSelected = computed(() => state.selected.length > 0);

  watch(isShow, (isShow) => {
    isShow && fetchKeyFiles();
  });

  /**
   * 获取结果文件列表
   */
  function fetchKeyFiles() {
    state.isLoading = true;
    getKeyFiles({ rootId: props.id })
      .then((res) => {
        state.data = res;
        state.downloadLoadings = res.map(() => false);
        state.fileLoadings = res.map(() => false);
        isAnomalies.value = false;
      })
      .catch(() => {
        state.data = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  /**
   * 获取结果文件地址
   */
  function getDownloadUrl(data: KeyFileItem, index: number) {
    state.fileLoadings[index] = true;
    getRedisFileUrls({
      root_id: props.id,
      paths: [data.path],
    }).then((res) => {
      if (res?.[data.path]) {
        copy(res?.[data.path]);
      }
    })
      .finally(() => {
        state.fileLoadings[index] = false;
      });
  }

  /**
   * 表格选中
   */
  function handleTableSelected({ isAll, checked, data, row }: TableSelectionData<KeyFileItem>) {
    // 全选 checkbox 切换
    if (isAll) {
      state.selected = checked ? [...data] : [];
      return;
    }

    // 单选 checkbox 选中
    if (checked) {
      const toggleIndex = state.selected.findIndex(item => item.domain === row.domain);
      if (toggleIndex === -1) {
        state.selected.push(row);
      }
      return;
    }

    // 单选 checkbox 取消选中
    const toggleIndex = state.selected.findIndex(item => item.domain === row.domain);
    if (toggleIndex > -1) {
      state.selected.splice(toggleIndex, 1);
    }
  }

  /**
   * 下载文件
   */
  function handleDownload(data: KeyFileItem[] = state.selected, index?: number) {
    if (data.length === 0) return;

    const hasIndexLoading = typeof index === 'number';
    if (hasIndexLoading) {
      state.downloadLoadings[index] = true;
    } else {
      state.isBatchDownloading = true;
    }
    const paths = data.map(item => item.path);
    getRedisFileUrls({
      root_id: props.id,
      paths,
    })
      .then((res = {}) => {
        const values = Object.values(res);
        const interval = setInterval(downloadFile, 600, values as string[]);
        function downloadFile(urls: string[]) {
          if (urls.length > 0) {
            const url = urls.pop();
            const a = document.createElement('a');
            a.style.display = 'none';
            document.body.appendChild(a);
            a.setAttribute('href', url as string);
            a.click();
            document.body.removeChild(a);
          } else {
            clearInterval(interval);
          }
        }
      })
      .finally(() => {
        if (hasIndexLoading) {
          state.downloadLoadings[index] = false;
        } else {
          state.isBatchDownloading = false;
        }
      });
  }

  /**
   * 删除 keys
   */
  async function handleDeleteKeys(data: KeyFileItem[] = state.selected) {
    if (data.length === 0) return;

    // size 为 0 无法操作删除 key
    if (data.filter(item => item.size === 0).length > 0) {
      messageWarn(t('批量操作中存在size为0的集群无法删除keys'));
      return;
    }

    const firstData = data[0];
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认从数据库中删除Key'),
      width: 500,
      extCls: 'redis-delete-keys-confirm',
      content: () => (
        <div class="delete-confirm">
          {
            data.length > 1
              ? (
                data.map((item, index) => (
                  <p class="delete-confirm__item">
                    {index + 1}.{item.domain}
                    {
                      item.cluster_alias
                        ? <span class="delete-confirm__desc">（{item.cluster_alias}）</span>
                        : null
                    }
                  </p>
                ))
              )
              : (
                  <p class="delete-confirm__item">
                    {t('集群')}：{firstData.domain}
                    {
                      firstData.cluster_alias
                        ? <span class="delete-confirm__desc">（{firstData.cluster_alias}）</span>
                        : null
                    }
                  </p>
                )
          }
          <p class="delete-confirm__item">{ t('删除Key_会将Key提取的对应内容进行删除_请谨慎操作') }</p>
        </div>
      ),
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: TicketTypes.REDIS_KEYS_DELETE,
            details: {
              delete_type: 'files',
              rules: data.map(item => ({
                cluster_id: item.cluster_id,
                domain: item.domain,
                path: item.name,
              })),
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }

  function handleClose() {
    isShow.value = false;
    state.selected = [];
    state.data = [];
    state.downloadLoadings = [];
    state.fileLoadings = [];
  }
</script>

<style lang="less" scoped>
  .result-files {
    &__table {
      :deep(.cluster-name) {
        line-height: 16px;

        &__alias {
          color: @light-gray;
        }
      }
    }
  }
</style>

<style lang="less">
  .redis-delete-keys-confirm {
    font-size: 20px;

    .delete-confirm {
      padding: 0 36px;
      text-align: left;

      &__item {
        padding-bottom: 4px;
        word-break: break-all;
      }

      &__desc {
        color: @light-gray;
      }
    }
  }
</style>
