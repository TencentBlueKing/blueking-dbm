<template>
  <BkDialog
    v-model:is-show="isShow"
    class="db-system-version-log-dialog"
    :draggable="false"
    :width="1100">
    <div
      ref="log"
      class="system-log-layout">
      <div class="layout-left">
        <ScrollFaker
          v-if="versionLogList"
          class="version-wraper">
          <BkLoading :loading="isVersionLogListLoading">
            <div
              v-for="(log, index) in versionLogList"
              :key="log[0]"
              class="log-tab"
              :class="{ active: log[0] === activeVersion }"
              @click="handleTabChange(log[0])">
              <div class="title">
                {{ log[0] }}
              </div>
              <div class="date">
                {{ log[1] }}
              </div>
              <div
                v-if="index === 0"
                class="new-flag">
                {{ t('当前版本') }}
              </div>
            </div>
          </BkLoading>
        </ScrollFaker>
      </div>
      <div class="layout-right">
        <ScrollFaker class="content-wraper">
          <BkLoading :loading="isVersionLogDetailLoading">
            <!-- eslint-disable vue/no-v-html -->
            <div
              v-if="logContent"
              class="markdowm-container"
              v-html="logContent" />
          </BkLoading>
        </ScrollFaker>
      </div>
    </div>
  </BkDialog>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getVersionLogDetail, getVersionLogList } from '@services/source/versionLog';

  const { t } = useI18n();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const activeVersion = ref('');

  const {
    loading: isVersionLogDetailLoading,
    data: logContent,
    run: fetchVersionLogDetail,
  } = useRequest(getVersionLogDetail, {
    manual: true,
  });

  const handleTabChange = (version: string) => {
    if (version === activeVersion.value) {
      return;
    }
    activeVersion.value = version;
    fetchVersionLogDetail({
      log_version: version,
    });
  };

  const { loading: isVersionLogListLoading, data: versionLogList } = useRequest(getVersionLogList, {
    onSuccess(data) {
      if (data.length > 0) {
        const [[lastVersion]] = data;
        handleTabChange(lastVersion);
      }
    },
  });
</script>
<style lang="less">
  .db-system-version-log-dialog {
    .bk-modal-body {
      padding: 0 !important;

      .bk-modal-header,
      .bk-modal-footer {
        display: none;
      }

      .bk-modal-content {
        padding: 0 !important;
      }
    }

    .system-log-layout {
      position: relative;
      display: flex;
      height: 600px;
      background: #fff;
    }

    .layout-left {
      flex: 0 0 180px;
      position: relative;
      padding: 40px 0;
      background: #fafbfd;

      &::after {
        position: absolute;
        top: 0;
        right: 0;
        width: 1px;
        height: 100%;
        background: #dcdee5;
        content: '';
      }
    }

    .layout-right {
      flex: 1;
      padding: 45px;
    }

    .version-wraper {
      max-height: 520px;
    }

    .content-wraper {
      max-height: 510px;
    }

    .log-tab {
      position: relative;
      display: flex;
      height: 54px;
      padding-left: 30px;
      cursor: pointer;
      border-bottom: 1px solid #dcdee5;
      flex-direction: column;
      justify-content: center;

      &.active {
        background: #fff;

        &::before {
          background: #3a84ff;
        }

        .title {
          color: #313238;
        }
      }

      &:first-child {
        border-top: 1px solid #dcdee5;
      }

      &::before {
        position: absolute;
        top: -1px;
        left: 0;
        width: 4px;
        height: 100%;
        border: 1px solid transparent;
        content: '';
      }

      .title {
        font-size: 16px;
        font-weight: bold;
        line-height: 22px;
        color: #63656e;
      }

      .date {
        font-size: 12px;
        line-height: 17px;
        color: #63656e;
      }

      .new-flag {
        position: absolute;
        top: 10px;
        right: 20px;
        display: flex;
        width: 58px;
        height: 20px;
        font-size: 12px;
        color: #fff;
        background: #699df4;
        border-radius: 2px;
        align-items: center;
        justify-content: center;
      }
    }

    .markdowm-container {
      font-size: 14px;
      color: #313238;

      h1,
      h2,
      h3,
      h4,
      h5 {
        height: auto;
        margin: 10px 0;
        font:
          normal 14px/1.5 'Helvetica Neue',
          Helvetica,
          Arial,
          'Lantinghei SC',
          'Hiragino Sans GB',
          'Microsoft Yahei',
          sans-serif;
        font-weight: bold;
        color: #34383e;
      }

      h1 {
        font-size: 30px;
      }

      h2 {
        font-size: 24px;
      }

      h3 {
        font-size: 18px;
      }

      h4 {
        font-size: 16px;
      }

      h5 {
        font-size: 14px;
      }

      em {
        font-style: italic;
      }

      div,
      p,
      font,
      span,
      li {
        line-height: 1.3;
      }

      p {
        margin: 0 0 1em;
      }

      table,
      table p {
        margin: 0;
      }

      ul,
      ol {
        padding: 0;
        margin: 0 0 1em 2em;
        text-indent: 0;
      }

      ul {
        padding: 0;
        margin: 10px 0 10px 15px;
        list-style-type: none;
      }

      ol {
        padding: 0;
        margin: 10px 0 10px 25px;
      }

      ol > li {
        line-height: 1.8;
        white-space: normal;
      }

      ul > li {
        padding-left: 15px !important;
        line-height: 1.8;
        white-space: normal;

        &::before {
          float: left;
          width: 6px;
          height: 6px;
          margin-top: calc(0.9em - 5px);
          margin-left: -15px;
          background: #000;
          border-radius: 50%;
          content: '';
        }
      }

      li > ul {
        margin-bottom: 10px;
      }

      li ol {
        padding-left: 20px !important;
      }

      ul ul,
      ul ol,
      ol ol,
      ol ul {
        margin-bottom: 0;
        margin-left: 20px;
      }

      ul.list-type-1 > li {
        padding-left: 0 !important;
        margin-left: 15px !important;
        list-style: circle !important;
        background: none !important;
      }

      ul.list-type-2 > li {
        padding-left: 0 !important;
        margin-left: 15px !important;
        list-style: square !important;
        background: none !important;
      }

      ol.list-type-1 > li {
        list-style: lower-greek !important;
      }

      ol.list-type-2 > li {
        list-style: upper-roman !important;
      }

      ol.list-type-3 > li {
        list-style: cjk-ideographic !important;
      }

      pre,
      code {
        width: 95%;
        padding: 0 3px 2px;
        font-family: Monaco, Menlo, Consolas, 'Courier New', monospace;
        font-size: 14px;
        color: #333;
        border-radius: 3px;
      }

      code {
        padding: 2px 4px;
        font-family: Consolas, monospace, tahoma, Arial;
        color: #d14;
        border: 1px solid #e1e1e8;
      }

      pre {
        display: block;
        padding: 9.5px;
        margin: 0 0 10px;
        font-family: Consolas, monospace, tahoma, Arial;
        font-size: 13px;
        word-break: break-all;
        word-wrap: break-word;
        white-space: pre-wrap;
        background-color: #f6f6f6;
        border: 1px solid #ddd;
        border: 1px solid rgb(0 0 0 / 15%);
        border-radius: 2px;
      }

      pre code {
        padding: 0;
        white-space: pre-wrap;
        border: 0;
      }

      blockquote {
        padding: 0 0 0 14px;
        margin: 0 0 20px;
        border-left: 5px solid #dfdfdf;
      }

      blockquote p {
        margin-bottom: 0;
        font-size: 14px;
        font-weight: 300;
        line-height: 25px;
      }

      blockquote small {
        display: block;
        line-height: 20px;
        color: #999;
      }

      blockquote small::before {
        content: '\2014 \00A0';
      }

      blockquote::before,
      blockquote::after {
        content: '';
      }
    }
  }
</style>
