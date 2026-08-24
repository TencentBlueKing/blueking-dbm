<template>
  <NoticeComponent
    :api-url="noticeApi"
    @show-alert-change="showNoticChange" />
  <Layout :style="{ '--notice-height': isShowBKNotice ? '40px' : '0px' }">
    <template #navigationHeaderRight>
      <SystemSearch
        class="mr-8"
        style="margin-left: auto" />
      <LocaleSwitch />
      <BkPopover
        click-content-auto-hide
        placement="bottom"
        theme="light top-action-menu-theme"
        trigger="click">
        <div class="top-action-btn mr-8">
          <DbIcon type="help-fill" />
        </div>
        <template #content>
          <div
            class="item"
            @click="handleShowSystemVersionLog">
            {{ t('版本日志') }}
          </div>
          <div
            class="item"
            @click="linkToDoc">
            {{ t('产品文档') }}
          </div>
        </template>
      </BkPopover>
      <BkLoginUserinfo
        style="position: relative; z-index: 999"
        :userinfo="userinfo">
        <template #action>
          <ActionItem
            v-if="systemEnvironStore.urls.BK_IAM_URL"
            :href="systemEnvironStore.urls.BK_IAM_URL"
            target="_blank">
            <template #icon>
              <DbIcon type="quanxianzhongxin" />
            </template>
            {{ t('权限中心') }}
          </ActionItem>
          <ActionItem
            v-if="systemEnvironStore.urls.BK_USER_MANAGE_URL"
            :href="systemEnvironStore.urls.BK_USER_MANAGE_URL"
            target="_blank">
            <template #icon>
              <DbIcon type="yonghu" />
            </template>
            {{ t('个人中心') }}
          </ActionItem>
          <ActionItem
            theme="danger"
            @click="handleSignOut">
            <template #icon>
              <DbIcon type="tuichu" />
            </template>
            {{ t('退出登录') }}
          </ActionItem>
        </template>
      </BkLoginUserinfo>
    </template>
    <template #content-header>
      <RouterBack />
    </template>
    <DbRouterView style="height: 100%" />
  </Layout>
  <SystemVersionLog v-model:is-show="isShowSystemVersionLog" />
  <AIBlueking />
</template>
<script setup lang="ts">
  import InfoBox from 'bkui-vue/lib/info-box';
  import urlJoin from 'url-join';
  import { onMounted, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import BkLoginUserinfo, { ActionItem } from '@blueking/login-userinfo';
  import NoticeComponent from '@blueking/notice-component';

  import { getLogout } from '@services/source/logout';

  import { useSQLTaskNotify } from '@hooks';

  import { useSystemEnviron, useUserProfile } from '@stores';

  import AIBlueking from '@components/ai-blueking/Index.vue';
  import DbRouterView from '@components/db-router-view/Index.vue';
  import LocaleSwitch from '@components/locale-switch/Index.vue';
  import RouterBack from '@components/router-back/Index.vue';
  import SystemSearch from '@components/system-search/Index.vue';
  import SystemVersionLog from '@components/system-version-log/Index.vue';

  import('@blueking/login-userinfo/vue3/vue3.css');

  import { checkDbConsole } from '@utils';

  import Layout from './layout/Index.vue';

  import('@blueking/notice-component/dist/style.css');

  const userProfileStore = useUserProfile();
  const { locale, t } = useI18n();
  const systemEnvironStore = useSystemEnviron();

  const documentTitles: Record<string, string> = {
    en: 'DBM | Tencent BlueKing',
    'zh-cn': '数据库管理 | 腾讯蓝鲸智云',
  };

  const noticeApi = urlJoin(window.BK_AJAX_URL, '/notice/announcements/');
  const isShowBKNotice = ref(false);
  const isShowSystemVersionLog = ref(false);

  const userinfo = computed(() => {
    return {
      name: userProfileStore.username,
      organization: userProfileStore.tenantId,
    };
  });

  watch(
    locale,
    () => {
      document.title = documentTitles[locale.value]!;
    },
    { immediate: true },
  );

  const showNoticChange = (value: boolean) => {
    isShowBKNotice.value = value;
  };

  const handleShowSystemVersionLog = () => {
    isShowSystemVersionLog.value = true;
  };

  const linkToDoc = () => {
    const url = systemEnvironStore.urls.BK_HELPER_URL;
    if (url) {
      window.open(url);
    }
  };

  const handleSignOut = () => {
    InfoBox({
      onConfirm: () => {
        window.HAS_LOGGED_IN = false;
        getLogout();
      },
      title: t('确认退出登录'),
    });
  };

  onMounted(() => {
    if (checkDbConsole('mysql.toolbox.sqlExecute') || checkDbConsole('tendbCluster.toolbox.sqlExecute')) {
      useSQLTaskNotify();
    }
  });
</script>
<style lang="less">
  .bk-popover[data-theme~='top-action-menu-theme'] {
    padding-right: 0 !important;
    padding-left: 0 !important;

    .item {
      display: flex;
      height: 32px;
      padding: 0 16px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      align-items: center;

      &.active,
      &:hover {
        color: #3a84ff;
        background-color: #eaf3ff;
      }
    }
  }

  .top-action-btn {
    position: relative;
    display: inline-flex;
    width: 32px;
    height: 32px;
    font-size: 16px;
    color: #979ba5;
    cursor: pointer;
    border-radius: 50%;
    transition: background 0.15s;
    align-items: center;
    justify-content: center;

    &:hover,
    &.active {
      color: @primary-color;
      background-color: #f0f1f5;
    }
  }

  .user-info-box {
    cursor: pointer;

    .username-text {
      padding-right: 4px;
      line-height: 32px;
    }

    .user-info-arrow {
      display: inline-block;
      font-size: 12px;
      transition: all 0.2s;

      &.is-active {
        transform: rotate(180deg);
      }
    }
  }
</style>
