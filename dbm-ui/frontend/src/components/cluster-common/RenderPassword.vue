<template>
  <BkLoading
    class="cluster-username-password-box"
    :loading="isLoading">
    <div class="item">
      <span class="item-label">{{ $t('集群名称') }}：</span>
      <span class="item-value">{{ result.cluster_name || '--' }}</span>
    </div>
    <div class="item">
      <span class="item-label">{{ $t('域名') }}：</span>
      <span class="item-value">{{ result.domain || '--' }}</span>
    </div>
    <div class="item">
      <span class="item-label">{{ $t('账号') }}：</span>
      <span class="item-value">{{ result.username || '--' }}</span>
      <span
        v-bk-tooltips="$t('复制账号及密码')"
        class="copy-btn">
        <i
          class="db-icon-copy"
          @click="handleCopy" />
      </span>
    </div>
    <div class="item">
      <span class="item-label">{{ $t('密码') }}：</span>
      <span class="item-value">{{ passwordText }}</span>
      <span
        class="password-btn"
        @click="handlePasswordToggle">
        <Unvisible v-if="isShowPassword" />
        <Eye v-else />
      </span>
    </div>
  </BkLoading>
</template>

<script setup lang="ts">
  import {
    Eye,
    Unvisible,
  } from 'bkui-vue/lib/icon';
  import { ref } from 'vue';

  import { getPassword } from '@services/pulsar';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const copy = useCopy();

  const { currentBizId } = useGlobalBizs();

  const isLoading = ref(true);
  const isShowPassword = ref(false);
  const result = ref({
    cluster_name: '',
    domain: '',
    username: '',
    password: '',
    token: '',
  });

  getPassword({
    bk_biz_id: currentBizId,
    cluster_id: props.clusterId,
  })
    .then((data) => {
      result.value = data;
    })
    .finally(() => {
      isLoading.value = false;
    });

  const passwordText = computed(() => {
    if (!isShowPassword.value) {
      return '******';
    }
    return result.value.password || '--';
  });


  const handleCopy = () => {
    const {
      username,
      password,
      token,
    } = result.value;
    copy(`${username} ${password} ${token}`);
  };

  const handlePasswordToggle = () => {
    isShowPassword.value = !isShowPassword.value;
  };

</script>

<style lang="less" scoped>
  .cluster-username-password-box {
    padding-bottom: 24px;

    .item {
      display: flex;
      padding: 8px 0;
      font-size: 12px;

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
        font-size: @font-size-normal;
        color: @primary-color;
        cursor: pointer;
      }
    }
  }
</style>
