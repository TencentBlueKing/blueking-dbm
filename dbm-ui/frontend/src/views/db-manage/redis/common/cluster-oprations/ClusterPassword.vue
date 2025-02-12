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
    class="cluster-password"
    :is-show="isShow"
    :quick-close="false"
    :title="title || t('获取访问方式')"
    @closed="handleClose">
    <BkLoading :loading="state.isLoading">
      <div class="copy-info">
        <BkButton
          text
          theme="primary"
          @click="handleCopyAll">
          {{ t('复制信息') }}
        </BkButton>
      </div>
      <div class="cluster-password-content">
        <div class="cluster-password-item">
          <span class="cluster-password-item-label">{{ t('集群名称') }}：</span>
          <span class="cluster-password-item-value">{{ state.data.cluster_name || '--' }}</span>
          <span
            v-bk-tooltips="t('复制集群名称')"
            class="copy-btn">
            <DbIcon
              type="copy"
              @click="copy(state.data.cluster_name)" />
          </span>
        </div>
        <div class="cluster-password-item">
          <span class="cluster-password-item-label">{{ t('域名') }}：</span>
          <span class="cluster-password-item-value">
            <span>{{ state.data.domain || '--' }}</span>
            <span
              v-bk-tooltips="t('复制域名')"
              class="copy-btn">
              <DbIcon
                type="copy"
                @click="copy(state.data.domain)" />
            </span>
          </span>
        </div>
        <div class="cluster-password-item">
          <span class="cluster-password-item-label">{{ t('密码') }}：</span>
          <span class="cluster-password-item-value">
            <span>{{ passwordText }}</span>
            <span
              class="password-btn"
              @click="handlePasswordToggle">
              <Unvisible v-if="isShowPassword" />
              <Eye v-else />
            </span>
            <span
              v-bk-tooltips="t('复制密码')"
              class="copy-btn">
              <DbIcon
                type="copy"
                @click="() => copy(state.data.password)" />
            </span>
          </span>
        </div>
      </div>
    </BkLoading>
    <BkLoading
      v-if="showClb"
      :loading="clbLoading">
      <div class="cluster-clb-main">
        <template
          v-for="(value, key) in dataObj"
          :key="key">
          <div
            v-if="dataObj[key].list[0].value"
            class="item-main-box">
            <div class="main-title">
              {{ dataObj[key].title }}
            </div>
            <div
              v-for="(item, index) in dataObj[key].list"
              :key="index"
              class="item-box">
              <div class="item-title">{{ item.title }}：</div>
              <div class="item-content">
                <span
                  v-overflow-tips
                  class="text-overflow">
                  {{ item.value }}
                </span>
                <DbIcon
                  v-bk-tooltips="t('复制n', { n: item.title })"
                  class="copy-btn"
                  type="copy"
                  @click="() => copy(item.value)" />
                <DbIcon
                  v-if="item.shareLink"
                  class="icon"
                  type="link"
                  @click="() => handleNavigateTo(item.shareLink)" />
              </div>
            </div>
          </div>
        </template>
      </div>
    </BkLoading>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { Eye, Unvisible } from 'bkui-vue/lib/icon';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterEntryDetailModel, {
    type ClbPolarisTargetDetails,
    type DnsTargetDetails,
  } from '@services/model/cluster-entry/cluster-entry-details';
  import { getClusterEntries } from '@services/source/clusterEntry';
  import { getRedisPassword } from '@services/source/redis';

  import { useGlobalBizs } from '@stores';

  import { execCopy } from '@utils';

  interface Props {
    title?: string;
    fetchParams: {
      bk_biz_id: number;
      cluster_id: number;
      db_type: string;
      type: string;
    };
    showClb?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
    showClb: true,
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const initDataObj = () => ({
    clb: {
      title: t('腾讯云负载均衡（CLB）'),
      list: [
        {
          title: 'IP',
          value: '',
          shareLink: '',
        },
        {
          title: t('CLB域名'),
          value: '',
          shareLink: '',
        },
      ],
    },
    polary: {
      title: t('CL5与北极星'),
      list: [
        {
          title: 'CL5',
          value: '',
          shareLink: '',
        },
        {
          title: t('北极星服务名称'),
          value: '',
          shareLink: '',
        },
      ],
    },
    nodes: {
      title: t('存储层（Nodes）'),
      list: [
        {
          title: t('域名'),
          value: '',
          shareLink: '',
        },
      ],
    },
  });

  const initData = () => ({
    cluster_name: '',
    domain: '',
    password: '',
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const isShowPassword = ref(false);
  const dataObj = ref(initDataObj());

  const state = reactive({
    isLoading: false,
    data: initData(),
  });

  const passwordText = computed(() => (isShowPassword.value ? state.data.password : '******'));

  const { loading: clbLoading, run: runGetClusterEntries } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (res) => {
      res.forEach((item) => {
        if (item.target_details.length) {
          if (item.isClb) {
            const targetDetailItem = (item as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
            dataObj.value.clb.list[0].value = `${targetDetailItem.clb_ip}:${targetDetailItem.port}`;
            dataObj.value.clb.list[1].value = `${targetDetailItem.clb_domain}:${targetDetailItem.port}`;
          } else if (item.isPolaris) {
            const targetDetailItem = (item as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
            dataObj.value.polary.list[0].value = targetDetailItem.polaris_l5;
            dataObj.value.polary.list[0].shareLink = targetDetailItem.url;
            dataObj.value.polary.list[1].value = `${targetDetailItem.polaris_name}:${targetDetailItem.port}`;
          } else if (item.isNodeEntry) {
            const targetDetailItem = (item as ClusterEntryDetailModel<DnsTargetDetails>).target_details[0];
            dataObj.value.nodes.list[0].value = `${item.entry}:${targetDetailItem.port}`;
          }
        }
      });
    },
  });

  // 获取集群密码
  watch(isShow, (isShow) => {
    if (isShow) {
      state.isLoading = true;
      getRedisPassword(props.fetchParams)
        .then((res) => {
          state.data = res;
        })
        .catch(() => {
          state.data = initData();
        })
        .finally(() => {
          state.isLoading = false;
        });
      if (props.showClb) {
        dataObj.value = initDataObj();
        runGetClusterEntries({
          cluster_id: props.fetchParams.cluster_id,
          bk_biz_id: currentBizId,
        });
      }
    }
  });

  const handleCopyAll = () => {
    let content = `${t('集群名称')}: ${state.data.cluster_name}\n${t('域名')}: ${state.data.domain}\n${t('Proxy密码')}: ${state.data.password}\n`;
    if (dataObj.value.clb.list[0].value) {
      // 存在CLB
      content = `${content}IP: ${dataObj.value.clb.list[0].value}\n${t('CLB域名')}: ${dataObj.value.clb.list[1].value}\n`;
    }
    if (dataObj.value.polary.list[0].value) {
      // 存在北极星
      content = `${content}CL5: ${dataObj.value.polary.list[0].value}\n${t('北极星服务名称')}: ${dataObj.value.polary.list[1].value}\n`;
    }
    if (dataObj.value.nodes.list[0].value) {
      // 存在存储层（Nodes）
      content = `${content}${t('存储层（Nodes）域名')}: ${dataObj.value.nodes.list[0].value}\n`;
    }
    copy(content);
  };

  const copy = (value: string) => {
    execCopy(value, t('复制成功，共n条', { n: 1 }));
  };

  const handleNavigateTo = (url: string) => {
    window.open(url);
  };

  const handlePasswordToggle = () => {
    isShowPassword.value = !isShowPassword.value;
  };

  const handleClose = () => {
    isShow.value = false;
    setTimeout(() => {
      state.data = initData();
      isShowPassword.value = false;
    }, 500);
  };
</script>

<style lang="less" scoped>
  .cluster-password {
    .bk-form-item {
      margin-bottom: 0;
    }

    :deep(.copy-info) {
      position: absolute;
      top: -18px;
      left: 160px;
    }

    :deep(.bk-form-label) {
      padding-right: 8px;
    }

    .cluster-password-content {
      padding-bottom: 8px;
      font-size: @font-size-mini;
    }

    .cluster-password-item {
      display: flex;
      padding-bottom: 16px;

      &:hover {
        .copy-btn {
          visibility: visible;
        }
      }

      .cluster-password-item-label {
        flex-shrink: 0;
        width: 100px;
        text-align: right;
      }

      .cluster-password-item-value {
        color: @title-color;
        word-break: break-all;
      }

      .copy-btn,
      .password-btn {
        display: inline-block;
        margin-left: 4px;
        font-size: @font-size-mini;
        color: @primary-color;
        cursor: pointer;
      }

      .copy-btn {
        visibility: hidden;
      }
    }

    .cluster-clb-main {
      display: flex;
      width: 100%;
      flex-direction: column;

      .item-main-box {
        display: flex;
        width: 100%;
        margin-bottom: 24px;
        flex-direction: column;

        .main-title {
          margin-bottom: 10px;
          font-size: 12px;
          font-weight: 700;
          color: #313238;
        }

        .item-box {
          display: flex;
          width: 100%;
          height: 28px;
          font-size: 12px;
          align-items: center;

          .item-title {
            width: 96px;
            color: #63656e;
            text-align: right;
          }

          .item-content {
            display: flex;
            overflow: hidden;
            color: #313238;
            flex: 1;
            align-items: center;

            &:hover {
              .copy-btn {
                visibility: visible;
              }
            }

            .icon {
              margin-left: 6px;
              color: #3a84ff;
              cursor: pointer;
            }

            .copy-btn {
              display: inline-block;
              margin-left: 6px;
              font-size: @font-size-mini;
              color: @primary-color;
              cursor: pointer;
              visibility: hidden;
            }
          }
        }
      }
    }
  }
</style>
