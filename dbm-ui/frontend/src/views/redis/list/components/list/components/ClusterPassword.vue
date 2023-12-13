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
    :title="title ||$t('获取访问方式')"
    @closed="handleClose">
    <BkLoading :loading="state.isLoading">
      <div class="cluster-password__content">
        <div class="cluster-password__item">
          <span class="cluster-password__item-label">{{ $t('集群名称') }}：</span>
          <span class="cluster-password__item-value">{{ state.data.cluster_name || '--' }}</span>
        </div>
        <div class="cluster-password__item">
          <span class="cluster-password__item-label">{{ $t('域名') }}：</span>
          <span class="cluster-password__item-value">
            <span>{{ state.data.domain || '--' }}</span>
            <span
              v-bk-tooltips="$t('复制')"
              class="password-btn">
              <i
                class="db-icon-copy"
                @click="copy(state.data.domain)" />
            </span>
          </span>
        </div>
        <div class="cluster-password__item">
          <span class="cluster-password__item-label">{{ $t('Proxy密码') }}：</span>
          <span class="cluster-password__item-value">
            <span>{{ passwordText }}</span>
            <span
              class="password-btn"
              @click="handlePasswordToggle">
              <Unvisible v-if="isShowPassword" />
              <Eye v-else />
            </span>
            <!-- <i
              class="db-icon-copy"
              @click="handleCopy" /> -->
          </span>
        </div>
      </div>
    </BkLoading>
    <BkLoading :loading="clbLoading">
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
              <div class="item-title">
                {{ item.title }}：
              </div>
              <div class="item-content">
                <span
                  v-overflow-tips
                  class="text-overflow">{{ item.value }}</span>
                <DbIcon
                  class="icon"
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
        {{ $t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import {
    Eye,
    Unvisible,
  } from 'bkui-vue/lib/icon';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterEntries } from '@services/source/cluster';
  import { getRedisPassword } from '@services/source/redis';
  import type { ClusterPasswordParams } from '@services/types/clusters';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

  interface Props {
    title?: string,
    fetchParams: ClusterPasswordParams,
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
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
  });

  const initData = () => ({
    cluster_name: '',
    domain: '',
    password: '',
  });

  const copy = useCopy();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const isShowPassword = ref(false);
  const dataObj = ref(initDataObj());

  const state = reactive({
    isLoading: false,
    data: initData(),
  });

  const passwordText = computed(() => (isShowPassword.value ? state.data.password : '******'));

  const {
    loading: clbLoading,
    run: runGetClusterEntries,
  } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (res) => {
      res.forEach((item) => {
        if (item.cluster_entry_type === 'clb') {
          dataObj.value.clb.list[0].value = item.target_details.clb_ip;
          dataObj.value.clb.list[1].value = item.target_details.clb_domain;
        } else if (item.cluster_entry_type === 'polaris') {
          dataObj.value.polary.list[0].value = item.target_details.polaris_l5;
          dataObj.value.polary.list[0].shareLink = item.target_details.url;
          dataObj.value.polary.list[1].value = item.target_details.polaris_name;
        }
      });
    },
  });

  // 获取集群密码
  watch(isShow, (isShow) => {
    if (isShow) {
      dataObj.value = initDataObj();
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
      runGetClusterEntries({
        cluster_id: props.fetchParams.cluster_id,
        bk_biz_id: currentBizId,
      });
    }
  });

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

    :deep(.bk-form-label) {
      padding-right: 8px;
    }

    &__content {
      padding-bottom: 8px;
      font-size: @font-size-mini;
    }

    &__item {
      display: flex;
      padding-bottom: 16px;

      &-label {
        flex-shrink: 0;
        width: 100px;
        text-align: right;
      }

      &-value {
        color: @title-color;
        word-break: break-all;

        .db-icon-copy,
        .password-btn {
          display: inline-block;
          margin-left: 4px;
          font-size: @font-size-normal;
          color: @primary-color;
          vertical-align: middle;
          cursor: pointer;
        }
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
            color: #63656E;
            text-align: right;
          }

          .item-content {
            display: flex;
            overflow: hidden;
            color: #313238;
            flex: 1;
            align-items: center;

            .icon {
              margin-left: 6px;
              color: #3A84FF;
              cursor: pointer;
            }
          }
        }
      }


    }
  }
</style>
