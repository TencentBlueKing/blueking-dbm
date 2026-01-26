<template>
  <div class="follow-up-record-item-main">
    <div class="left-sign-main">
      <div class="sign-main">
        <div
          v-if="data.isStart || (data.isEnd && isRiskDone)"
          class="circle-status-main"
          :class="{ 'is-start': data.isStart }"></div>
        <DbIcon
          v-else
          svg
          type="touxiang" />
      </div>
      <div
        v-show="showLine"
        class="line-main"></div>
    </div>
    <div class="record-content-main">
      <div class="record-info">
        <div
          class="main-title"
          :class="{ 'is-start-end': data.isStart || data.isEnd }">
          <div class="title-display">
            <span>{{ data.creator }}</span>
            <span class="ml-4">{{ titleStatusDisplay }}</span>
          </div>
          <div
            v-if="!isRiskDone && data.is_follow_up_owner && !data.isStart"
            class="operate-main">
            <AuthTemplate
              action-id="risk_memo_manage"
              :biz-id="bizId"
              :permission="managePermission">
              <div
                class="operate-item"
                @click="handleClickEdit">
                <DbIcon type="edit" />
              </div>
            </AuthTemplate>
            <BkPopConfirm
              :confirm-config="{
                theme: 'danger',
                loading: deleteLoading,
              }"
              :confirm-text="t('删除')"
              :content="t('删除操作无法撤回，请谨慎操作！')"
              placement="bottom-start"
              :title="t('确认删除该跟进内容？')"
              trigger="click"
              :width="288"
              @confirm="handleDelete">
              <AuthTemplate
                action-id="risk_memo_manage"
                :biz-id="bizId"
                :permission="managePermission">
                <div class="operate-item">
                  <DbIcon type="delete" />
                </div>
              </AuthTemplate>
            </BkPopConfirm>
          </div>
        </div>
        <div class="time-display">
          <span>{{ utcDisplayTime(data.create_at) }}</span>
          <template v-if="!isRiskDone && !data.isStart && data.create_at !== data.update_at">
            <span class="ml-4 mr-4">(</span>
            <I18nT
              keypath="people于date修改了跟进内容"
              tag="span">
              <span>{{ data.updater }}</span>
              <span>{{ utcDisplayTime(data.update_at) }}</span>
            </I18nT>
            <span class="ml-4 mr-4">)</span>
          </template>
        </div>
      </div>
      <template v-if="!data.isStart">
        <RiskMemoEditor
          v-if="!isEdit"
          class="editor-content-view"
          :model-value="viewerHtml"
          readonly />
        <div
          v-else
          class="edit-follow-up">
          <RiskMemoEditor v-model="editorHtml" />
          <div class="operate-btn-main">
            <BkButton
              v-bk-tooltips="{
                disabled: editorHtml !== data.content,
                content: t('暂无改动，无需保存'),
              }"
              class="w-88"
              :disabled="editorHtml === data.content"
              :loading="updateLoading"
              theme="primary"
              @click="handleClickSave">
              {{ t('保存') }}
            </BkButton>
            <BkButton
              class="w-88"
              @click="handleClickCancel">
              {{ t('取消') }}
            </BkButton>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { filterXss } from '@blueking/xss-filter';

  import { deleteRiskFollowUp, updateRiskFollowUp } from '@services/source/riskMemo';

  import { utcDisplayTime } from '@utils';

  import RiskMemoEditor from '../../RickMemoEditor.vue';
  import { type FollowUpList } from '../Index.vue';

  interface Props {
    bizId?: number;
    data: FollowUpList[number];
    isRiskDone: boolean;
    managePermission?: boolean;
    riskId: number;
    showLine?: boolean;
  }

  type Emits = (e: 'updateSuccess') => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: 0,
    managePermission: true,
    showLine: true,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isEdit = ref(false);
  const editorHtml = ref('');

  const viewerHtml = computed(() =>
    filterXss(props.data.content, {
      imgSrcMode: 'none',
    }),
  );
  const titleStatusDisplay = computed(() => {
    if (props.data.isStart) {
      return t('创建风险');
    } else if (props.isRiskDone && props.data.isEnd) {
      return t('结项');
    }
    return t('添加跟进');
  });

  const { loading: updateLoading, run: updateFollowUp } = useRequest(updateRiskFollowUp, {
    manual: true,
    onSuccess: () => {
      emits('updateSuccess');
      isEdit.value = false;
    },
  });

  const { loading: deleteLoading, run: runDeleteFollowUp } = useRequest(deleteRiskFollowUp, {
    manual: true,
    onSuccess: () => {
      emits('updateSuccess');
    },
  });

  watch(
    () => props.data.content,
    () => {
      editorHtml.value = props.data.content || '';
    },
    {
      immediate: true,
    },
  );

  const handleClickEdit = () => {
    isEdit.value = true;
  };

  const handleDelete = () => {
    runDeleteFollowUp({ id: props.data.id });
  };

  const handleClickSave = () => {
    updateFollowUp({
      content: editorHtml.value,
      id: props.data.id,
      risk: props.riskId,
    });
  };

  const handleClickCancel = () => {
    isEdit.value = false;
  };
</script>
<style lang="less">
  .follow-up-record-item-main {
    display: flex;
    font-size: 12px;

    .left-sign-main {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-right: 8px;

      .sign-main {
        display: flex;
        width: 40px;
        font-size: 40px;
        justify-content: center;

        .circle-status-main {
          width: 16px;
          height: 16px;
          background-color: #979ba5;
          border: solid 4px #f5f7fa;
          border-radius: 50%;

          &.is-start {
            background-color: #3a84ff;
            border-color: #f0f5ff;
          }
        }
      }

      .line-main {
        flex: 1;
        width: 2px;
        background: #eaebf0;
      }
    }

    .record-content-main {
      flex: 1;
      margin-bottom: 24px;

      .record-info {
        margin-bottom: 8px;

        .main-title {
          display: flex;
          gap: 4px;
          height: 20px;
          align-items: center;

          &.is-start-end {
            margin-top: -2px;
          }

          .title-display {
            font-size: 12px;
            font-weight: 700;
            color: #313238;
          }

          .operate-main {
            display: flex;

            .operate-item {
              display: flex;
              width: 20px;
              height: 14px;
              color: #979ba5;
              cursor: pointer;
              border-radius: 8px;
              align-items: center;
              justify-content: center;

              &:hover {
                color: #fff;
                background: #3a84ff;
              }
            }
          }
        }

        .time-display {
          height: 20px;
          line-height: 20px;
          color: #979ba5;
        }
      }

      .editor-content-view {
        position: relative;
        width: 100%;
        padding: 16px;
        overflow: auto;
        font-family: MicrosoftYaHei, sans-serif;
        color: #313238;
        background: #f5f7fa;
        border-radius: 8px;
      }
    }
  }
</style>
