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
  <BkLoading
    class="cluster-username-password-box"
    :loading="isLoading">
    <div class="copy-info">
      <BkButton
        text
        theme="primary"
        @click="() => handleCopy('all')">
        {{ t('复制信息') }}
      </BkButton>
    </div>
    <div class="item">
      <span class="item-label">{{ t('集群名称') }}：</span>
      <span class="item-value">{{ result.cluster_name || '--' }}</span>
      <span
        v-bk-tooltips="t('复制集群名称')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('cluster_name')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ t('域名') }}：</span>
      <span class="item-value">{{ domainDisplay }}</span>
      <span
        v-bk-tooltips="t('复制域名')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('domain')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ isPulsar ? t('Manager 账号') : t('账号') }}：</span>
      <span class="item-value">{{ result.username || '--' }}</span>
      <span
        v-bk-tooltips="t('复制账号')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('username')" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ isPulsar ? t('Manager 密码') : t('密码') }}：</span>
      <span class="item-value">{{ passwordText }}</span>
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
          @click="() => handleCopy('password')" />
      </span>
    </div>
    <div
      v-if="isKafka"
      class="item">
      <span class="item-label">{{ t('安全认证') }}：</span>
      <span class="item-value">
        <p>security.protocol=SASL_PLAINTEXT</p>
        <p>sasl.mechanism=SCRAM-SHA-512</p>
        <p>
          sasl.jaas.config=org.apache.{{ dbType }}.common.security.scram.ScramLoginModule required username="{{
            result.username
          }}" password="{{ scPasswordText }}";
          <span
            class="password-btn"
            @click="handleSCPasswordToggle">
            <Unvisible v-if="isShowSCPassword" />
            <Eye v-else />
          </span>
          <span
            v-bk-tooltips="t('复制安全认证')"
            class="copy-btn">
            <DbIcon
              type="copy"
              @click="() => handleCopy('security_certification')" />
          </span>
        </p>
      </span>
    </div>
    <div
      v-if="isPulsar"
      class="item">
      <span class="item-label">Token：</span>
      <span class="item-value">{{ tokenText }}</span>
      <span
        class="password-btn"
        @click="handleTokenToggle">
        <Unvisible v-if="isShowToken" />
        <Eye v-else />
      </span>
      <span
        v-bk-tooltips="t('复制 Token')"
        class="copy-btn">
        <DbIcon
          type="copy"
          @click="() => handleCopy('token')" />
      </span>
    </div>
  </BkLoading>
  <BkLoading
    v-if="isClbShow"
    :loading="clbLoading">
    <div class="cluster-render-password-clb">
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
</template>

<script setup lang="ts">
  import { Eye, Unvisible } from 'bkui-vue/lib/icon';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterEntryDetailModel, {
    type ClbPolarisTargetDetails,
  } from '@services/model/cluster-entry/cluster-entry-details';
  import { getClusterEntries } from '@services/source/clusterEntry';
  import { getDorisPassword } from '@services/source/doris';
  import { getEsPassword } from '@services/source/es';
  import { getHdfsPassword } from '@services/source/hdfs';
  import { getKafkaPassword } from '@services/source/kafka';
  import { getPulsarPassword } from '@services/source/pulsar';

  import { DBTypes } from '@common/const';

  import { execCopy } from '@utils';

  interface Props {
    clusterId: number;
    dbType?: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const initDataObj = () => ({
    clb: {
      list: [
        {
          shareLink: '',
          title: 'IP',
          value: '',
        },
        {
          shareLink: '',
          title: t('CLB域名'),
          value: '',
        },
      ],
      title: t('腾讯云负载均衡（CLB）'),
    },
    polary: {
      list: [
        {
          shareLink: '',
          title: 'CL5',
          value: '',
        },
        {
          shareLink: '',
          title: t('北极星服务名称'),
          value: '',
        },
      ],
      title: t('CL5与北极星'),
    },
  });

  const isLoading = ref(true);
  const isShowPassword = ref(false);
  const isShowSCPassword = ref(false);
  const isShowToken = ref(false);
  const result = ref({
    access_port: 0,
    cluster_name: '',
    domain: '',
    password: '',
    token: '',
    username: '',
  });

  const dataObj = ref(initDataObj());

  const isPulsar = computed(() => props.dbType === DBTypes.PULSAR);
  const isKafka = computed(() => props.dbType === DBTypes.KAFKA);
  const isClbShow = computed(() => props.dbType === DBTypes.ES);

  const domainDisplay = computed(() => {
    if (isPulsar.value) {
      return result.value.domain || '--';
    }

    return `${result.value.domain}:${result.value.access_port}`;
  });

  const passwordText = computed(() => {
    if (!isShowPassword.value) {
      return '******';
    }
    return result.value.password || '--';
  });
  const scPasswordText = computed(() => {
    if (!isShowSCPassword.value) {
      return '******';
    }
    return result.value.password || '--';
  });

  const tokenText = computed(() => {
    if (!isShowToken.value) {
      return '******';
    }
    return result.value.token || '--';
  });

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
          }
        }
      });
    },
  });

  const serviceMap: Record<string, typeof getPulsarPassword> = {
    [DBTypes.DORIS]: getDorisPassword,
    [DBTypes.ES]: getEsPassword,
    [DBTypes.HDFS]: getHdfsPassword,
    [DBTypes.KAFKA]: getKafkaPassword,
    [DBTypes.PULSAR]: getPulsarPassword,
  };

  watch(
    () => props.dbType,
    () => {
      if (props.dbType && props.dbType in serviceMap) {
        const getPasswordHandler = serviceMap[props.dbType];
        getPasswordHandler({ cluster_id: props.clusterId })
          .then((data) => {
            result.value = data;
          })
          .finally(() => {
            isLoading.value = false;
          });
        if (isClbShow.value) {
          dataObj.value = initDataObj();
          runGetClusterEntries({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            cluster_id: props.clusterId,
          });
        }
      }
    },
    {
      immediate: true,
    },
  );

  const handleCopy = (type: string) => {
    const { access_port: accessPort, cluster_name: clusterName, domain, password, token, username } = result.value;

    const domainPort = `${domain}:${accessPort}`;
    let passwordToken = password;
    if (token) {
      passwordToken = `${password} ${token}`;
    }

    let content = `${t('集群名称')}: ${clusterName}\n${t('域名')}: ${domainPort}\n${t('账号')}: ${username}\n${t('密码')}: ${passwordToken}`;
    if (isPulsar.value) {
      content = `${t('集群名称')}: ${clusterName}\n${t('域名')}: ${domain}\n${t('Manager 账号')}: ${username}\n${t('Manager 密码')}: ${password}\nToken: ${token}`;
    }
    let securityInfo = '';
    if (isKafka.value) {
      securityInfo = `security.protocol=SASL_PLAINTEXT\nsasl.mechanism=SCRAM-SHA-512\nsasl.jaas.config=org.apache.${props.dbType}.common.security.scram.ScramLoginModule required username="${username}" password="${password}";`;
      content = `${content}\n${t('安全认证')}: ${securityInfo}`;
    }

    if (isClbShow.value) {
      if (dataObj.value.clb.list[0].value) {
        // 存在CLB
        content = `${content}IP: ${dataObj.value.clb.list[0].value}\n${t('CLB域名')}: ${dataObj.value.clb.list[1].value}\n`;
      }
      if (dataObj.value.polary.list[0].value) {
        // 存在北极星
        content = `${content}CL5: ${dataObj.value.polary.list[0].value}\n${t('北极星服务名称')}: ${dataObj.value.polary.list[1].value}\n`;
      }
    }

    switch (type) {
      case 'cluster_name':
        copy(clusterName);
        break;
      case 'domain':
        if (isPulsar.value) {
          copy(domain);
          return;
        }

        copy(domainPort);
        break;
      case 'username':
        copy(username);
        break;
      case 'password':
        copy(passwordToken);
        break;
      case 'security_certification':
        copy(securityInfo);
        break;
      default:
        copy(content);
        break;
    }
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

  const handleSCPasswordToggle = () => {
    isShowSCPassword.value = !isShowSCPassword.value;
  };

  const handleTokenToggle = () => {
    isShowToken.value = !isShowToken.value;
  };
</script>

<style lang="less">
  .cluster-username-password-box {
    padding-bottom: 24px;

    .copy-info {
      position: absolute;
      top: -18px;
      left: 160px;
    }

    .item {
      display: flex;
      padding: 8px 0;
      font-size: 12px;

      &:hover {
        .copy-btn {
          visibility: visible;
        }
      }

      .item-label {
        flex-shrink: 0;
        width: 100px;
        text-align: right;
      }

      .item-value {
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
  }

  .cluster-render-password-clb {
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
</style>
