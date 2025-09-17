<template>
  <DbFormItem
    class="notification-setting-channel-item"
    :label="t('发送渠道')"
    property="channels"
    required
    :rules="channelsRules">
    <BkLoading :loading="fetchLoading">
      <div class="channel-content">
        <div
          v-for="item in channelList"
          :key="item.type"
          class="channel-item mr-32">
          <BkCheckbox v-model="item.checked">
            <div class="checkbox-item">
              <img
                class="mr-4"
                height="20"
                :src="`data:image/png;base64,${item.icon}`"
                width="20" />
              {{ item.label }}
            </div>
          </BkCheckbox>
          <BkInput
            v-if="InputMessageTypes.includes(item.type) && item.checked"
            v-model="item.inputValue"
            class="ml-16"
            clearable
            :placeholder="t('请输入群 ID')"
            style="width: 240px" />
        </div>
      </div>
    </BkLoading>
  </DbFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAlarmGroupNotifyList } from '@services/source/monitorNoticeGroup';

  import { InputMessageTypes } from '@common/const';

  interface Props {
    data: Record<string, boolean | string>;
  }

  interface Exposes {
    getValue: () => Props['data'];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const channelsRules = [
    {
      message: t('请输入群 ID'),
      required: true,
      validator() {
        // 消息类型为输入框的有勾选，需校验
        const inputMessageTypeMap = Object.fromEntries(InputMessageTypes.map((inputTypeItem) => [inputTypeItem, true]));
        return channelList.value.every((channelItem) => {
          if (inputMessageTypeMap[channelItem.type] && channelItem.checked) {
            return !!channelItem.inputValue;
          }
          return true;
        });
      },
    },
  ];

  const channelList = ref<
    {
      checked: boolean;
      icon: string;
      inputValue: string;
      label: string;
      type: string;
    }[]
  >([]);

  const { data: alarmGroupNotifyList, loading: fetchLoading } = useRequest(getAlarmGroupNotifyList);

  watch(
    () => [props.data, alarmGroupNotifyList.value],
    () => {
      if (alarmGroupNotifyList.value) {
        channelList.value = alarmGroupNotifyList.value.reduce<UnwrapRef<typeof channelList>>((prev, notifyItem) => {
          // 消息类型有开启才展示
          if (notifyItem.is_active) {
            // 结合接口数据进行回显
            const isExist = _.has(props.data, notifyItem.type);
            const channelItem = InputMessageTypes.includes(notifyItem.type)
              ? {
                  checked: isExist && props.data[notifyItem.type] ? true : false,
                  inputValue: isExist ? (props.data[notifyItem.type] as string) : '',
                }
              : {
                  checked: isExist ? (props.data[notifyItem.type] as boolean) : false,
                  inputValue: '',
                };

            return prev.concat(Object.assign(notifyItem, channelItem));
          }
          return prev;
        }, []);
      }
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return Object.fromEntries(
        channelList.value.map((channelItem) => {
          if (InputMessageTypes.includes(channelItem.type)) {
            return [channelItem.type, channelItem.inputValue];
          } else {
            return [channelItem.type, channelItem.checked];
          }
        }),
      );
    },
  });
</script>

<style lang="less">
  .notification-setting-channel-item {
    .channel-content {
      display: flex;
      flex-wrap: wrap;

      .channel-item {
        display: flex;
        align-items: center;

        .checkbox-item {
          display: flex;
          align-items: center;
        }
      }
    }
  }
</style>
