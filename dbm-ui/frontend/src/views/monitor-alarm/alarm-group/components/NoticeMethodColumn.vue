<template>
  <TableColumn
    col-key="notice_ways"
    :filter="columnFilter.notice_ways"
    :title="t('通知方式')"
    :width="420">
    <template #default="{ row }: { row: NoticGroupModel }">
      <div class="notice-method-column">
        <div
          v-for="item in row.details.alert_notice[0].notify_config"
          :key="item.level"
          class="notice-method-item">
          <div :class="[`notice-method-${levelMap[item.level].type}`]">
            <span class="ml-4">{{ levelMap[item.level].label }}</span>
          </div>
          <template v-if="item.notice_ways.length > 0">
            <DbIcon
              v-for="noticeItem in item.notice_ways"
              :key="noticeItem.name"
              v-bk-tooltips="{
                content: `${messageInfoMap[noticeItem.name as keyof typeof messageInfoMap]?.label}`,
              }"
              class="notice-method-icon"
              :type="messageInfoMap[noticeItem.name as keyof typeof messageInfoMap]?.icon">
            </DbIcon>
          </template>
          <span v-else>--</span>
        </div>
      </div>
    </template>
  </TableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import NoticGroupModel from '@services/model/notice-group/notice-group';

  import { useColumnFilter } from './../useColumnFilter.ts';

  const { t } = useI18n();
  const { data: columnFilter } = useColumnFilter();

  const levelMap = {
    1: {
      label: t('致命'),
      level: 1,
      type: 'error',
    },
    2: {
      label: t('预警'),
      level: 2,
      type: 'warning',
    },
    3: {
      label: t('提醒'),
      level: 3,
      type: 'default',
    },
  };

  const messageInfoMap = Object.fromEntries(NoticGroupModel.NoticeMethodList.map((item) => [item.type, item]));
</script>

<style lang="less">
  .notice-method-column {
    display: flex;
    align-items: center;
    gap: 8px;

    .notice-method-item {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 130px;

      .notice-method-default {
        color: @primary-color;
        border-left: 4px solid @primary-color;
      }

      .notice-method-warning {
        color: @warning-color;
        border-left: 4px solid @warning-color;
      }

      .notice-method-error {
        color: @danger-color;
        border-left: 4px solid @danger-color;
      }

      .notice-method-icon {
        font-size: 16px;
        color: #7d828c;
        cursor: pointer;
      }
    }
  }
</style>
