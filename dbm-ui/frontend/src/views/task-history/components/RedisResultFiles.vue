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
    :title="t('查看结果文件')"
    :width="1140"
    @closed="handleClose">
    <div class="mb-24">
      <span
        v-bk-tooltips="{
          disabled: hasSelected,
          content: t('请选择结果项'),
        }"
        class="inline-block">
        <BkButton
          class="mr-8"
          :disabled="!hasSelected"
          :loading="state.isBatchDownloading"
          @click="() => handleBatchDownload()">
          {{ t('打包下载') }}
        </BkButton>
      </span>
      <span
        v-if="showDelete"
        v-bk-tooltips="{
          disabled: hasSelected,
          content: t('请选择结果项'),
        }"
        class="inline-block">
        <BkButton @click="handleDeleteKeys()">
          {{ t('删除Key') }}
        </BkButton>
      </span>
    </div>
    <BkLoading :loading="state.isLoading">
      <PrimaryTable
        class="result-files-table"
        :columns="columns"
        :data="state.data"
        :height="460"
        row-key="path"
        :selected-row-keys="selectedRowKeys"
        @select-change="handleSelectChange">
        <template #empty>
          <EmptyStatus
            :is-anomalies="isAnomalies"
            :is-searching="false"
            @refresh="fetchKeyFiles" />
        </template>
      </PrimaryTable>
    </BkLoading>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { batchDownloadDirs, createBkrepoAccessToken } from '@services/source/storage';
  import { getKeyFiles } from '@services/source/taskflow';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { downloadUrl, execCopy, generateBkRepoDownloadUrl, messageWarn } from '@utils';

  type KeyFileItem = ServiceReturnType<typeof getKeyFiles>[number];

  interface Props {
    id: string;
    showDelete?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    showDelete: true,
  });

  const isShow = defineModel<boolean>({
    default: false,
    required: true,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const isAnomalies = ref(false);

  const state = reactive({
    data: [] as KeyFileItem[],
    downloadLoadings: [] as boolean[],
    fileLoadings: [] as boolean[],
    isBatchDownloading: false,
    isLoading: false,
    selected: [] as KeyFileItem[],
  });

  const columns: PrimaryTableCol[] = [
    {
      colKey: 'row-select',
      type: 'multiple',
      width: 52,
    },
    {
      colKey: 'name',
      ellipsis: true,
      title: t('目录'),
    },
    {
      colKey: 'size_display',
      title: t('大小'),
      width: 100,
    },
    {
      cell: (_, { row }) => {
        const data = row as KeyFileItem;
        return (
          <div
            v-overflow-tips={{
              allowHTML: true,
              content: `
              <p>${t('域名')}：${data.domain}</p>
              ${data.cluster_alias ? `<p>${'集群别名'}：${data.cluster_alias}</p>` : null}
            `,
            }}
            class='cluster-name text-overflow'>
            <span>{data.domain}</span>
            <br />
            <span class='cluster-name-alias'>{data.cluster_alias}</span>
          </div>
        );
      },
      colKey: 'files',
      title: t('集群'),
    },
    {
      colKey: 'created_time',
      title: t('提取时间'),
      width: 150,
    },
    {
      cell: (_, { row, rowIndex }) => (
        <div>
          <bk-button
            class='mr-8'
            loading={state.downloadLoadings[rowIndex]}
            text
            theme='primary'
            onClick={() => handleDownloadFile(row as KeyFileItem, rowIndex)}>
            {t('下载')}
          </bk-button>
          <bk-button
            loading={state.fileLoadings[rowIndex]}
            text
            theme='primary'
            onClick={() => getDownloadUrl(row as KeyFileItem, rowIndex)}>
            {t('复制文件地址')}
          </bk-button>
        </div>
      ),
      colKey: 'operations',
      title: t('操作'),
      width: 200,
    },
  ];

  const selectedRowKeys = ref<string[]>([]);

  const hasSelected = computed(() => state.selected.length > 0);

  watch(isShow, (isShow) => {
    if (isShow) {
      fetchKeyFiles();
    }
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
    createBkrepoAccessToken({ file_path: data.path })
      .then((tokenResult) => {
        const url = generateBkRepoDownloadUrl(tokenResult);
        execCopy(url);
      })
      .finally(() => {
        state.fileLoadings[index] = false;
      });
  }

  /**
   * 表格选中
   */
  function handleSelectChange(value: (number | string)[], { selectedRowData }: { selectedRowData: unknown[] }) {
    selectedRowKeys.value = value as string[];
    state.selected = selectedRowData as KeyFileItem[];
  }

  /**
   * 打包下载文件
   */
  function handleBatchDownload() {
    if (state.selected.length === 0) {
      return;
    }
    state.isBatchDownloading = true;
    const paths = state.selected.map((item) => item.path);
    batchDownloadDirs({ file_path_list: paths })
      .then((result) => {
        const values = Object.values(result);
        const interval = setInterval(downloadFile, 600, values);
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
        state.isBatchDownloading = false;
      });
  }

  /**
   * 下载单个文件
   */
  function handleDownloadFile(data: KeyFileItem, index: number) {
    state.downloadLoadings[index] = true;

    createBkrepoAccessToken({ file_path: data.path })
      .then((tokenResult) => {
        const url = generateBkRepoDownloadUrl(tokenResult);
        downloadUrl(url);
      })
      .finally(() => {
        state.downloadLoadings[index] = false;
      });
  }

  /**
   * 删除 keys
   */
  async function handleDeleteKeys(data: KeyFileItem[] = state.selected) {
    if (data.length === 0) return;

    // size 为 0 无法操作删除 key
    if (data.filter((item) => item.size === 0).length > 0) {
      messageWarn(t('批量操作中存在size为0的集群无法删除keys'));
      return;
    }

    const firstData = data[0];
    InfoBox({
      content: () => (
        <div class='delete-confirm'>
          {data.length > 1 ? (
            data.map((item, index) => (
              <p class='delete-confirm-item'>
                {index + 1}.{item.domain}
                {item.cluster_alias ? <span class='delete-confirm-desc'>（{item.cluster_alias}）</span> : null}
              </p>
            ))
          ) : (
            <p class='delete-confirm-item'>
              {t('集群')}：{firstData.domain}
              {firstData.cluster_alias ? <span class='delete-confirm-desc'>（{firstData.cluster_alias}）</span> : null}
            </p>
          )}
          <p class='delete-confirm-item'>{t('删除Key_会将Key提取的对应内容进行删除_请谨慎操作')}</p>
        </div>
      ),
      extCls: 'redis-delete-keys-confirm',
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            details: {
              delete_type: 'files',
              rules: data.map((item) => ({
                cluster_id: item.cluster_id,
                domain: item.domain,
                path: item.name,
              })),
            },
            ticket_type: TicketTypes.REDIS_KEYS_DELETE,
          };
          await createTicket(params).then((res) => {
            ticketMessage(res.id);
          });
          return true;
        } catch {
          return false;
        }
      },
      title: t('确认从数据库中删除Key'),
      type: 'warning',
      width: 500,
    });
  }

  function handleClose() {
    isShow.value = false;
    selectedRowKeys.value = [];
    state.selected = [];
    state.data = [];
    state.downloadLoadings = [];
    state.fileLoadings = [];
  }
</script>

<style lang="less" scoped>
  .result-files {
    .result-files-table {
      :deep(.cluster-name) {
        line-height: 16px;

        .result-files-alias {
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

      .delete-confirm-item {
        padding-bottom: 4px;
        word-break: break-all;
      }

      .delete-confirm-desc {
        color: @light-gray;
      }
    }
  }
</style>
