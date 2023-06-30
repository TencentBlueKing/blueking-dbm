<template>
  <div class="collect-serach-params">
    <span>
      <BkPopover
        :is-show="isShowForm"
        theme="light"
        trigger="manual"
        :width="275">
        <span
          v-bk-tooltips="{
            disabled: !isDisabled,
            content: t('搜索条件为空')
          }">
          <BkButton
            :disabled="isDisabled"
            @click="handleShowForm">
            {{ t('收藏条件') }}
          </BkButton>
        </span>
        <template #content>
          <div style="padding: 10px;">
            <div
              class="mb-12"
              style="font-size: 14px; line-height: 22px; color: #313238;">
              {{ t('设置为收藏条件') }}
            </div>
            <DbForm
              ref="formRef"
              form-type="vertical"
              :model="formData"
              :rules="rules">
              <DbFormItem
                :label="t('条件名称')"
                property="name"
                required>
                <BkInput
                  v-model="formData.name"
                  @keyup="(value, event) => handleKeyup(value, event as KeyboardEvent)" />
              </DbFormItem>
            </DbForm>
            <div
              class="mt-16"
              style="text-align: right">
              <BkButton
                :loading="isSubmiting"
                size="small"
                theme="primary"
                @click="handleSubmit">
                {{ t('确定') }}
              </BkButton>
              <BkButton
                class="ml-8"
                size="small"
                @click="handleCancel">
                {{ t('取消') }}
              </BkButton>
            </div>
          </div>
        </template>
      </BkPopover>
    </span>
    <template v-if="list.length > 0">
      <div class="line" />
      <BkSelect
        v-model="collectName"
        filterable
        :input-search="false"
        :placeholder="t('请选择收藏的条件')"
        style="width: 366px"
        @change="handleCollectChange">
        <BkOption
          v-for="(item, index) in list"
          :key="`${item.name}_${index}`"
          :label="item.name"
          :value="item.name">
          <div class="collect-serach-params-item">
            <div>{{ item.name }}</div>
            <BkPopConfirm
              :content="t('删除后将不可恢复，请谨慎操作！')"
              :title="t('确认删除该收藏？')"
              trigger="click"
              @confirm="handleRemove(item)">
              <div
                class="remove-btn"
                @click.stop="">
                <DbIcon type="close" />
              </div>
            </BkPopConfirm>
          </div>
        </BkOption>
      </BkSelect>
    </template>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    reactive,
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getProfile,
    upsertProfile,
  } from '@services/common';

  interface Props {
    searchParams: Record<string, any>
  }
  interface Emits{
    (e: 'change', value: Props['searchParams']): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const PRIMARY_KEY = 'resource_pool_search_params';

  const { t } = useI18n();

  const formRef = ref();
  const isShowForm = ref(false);
  const isSubmiting = ref(false);
  const collectName = ref('');
  const list = shallowRef<{name: string, params: Props['searchParams']}[]>([]);

  const formData = reactive({
    name: '',
  });

  const isDisabled = computed(() => {
    console.log('isDisabled = ', props.searchParams);
    return Object.keys(props.searchParams).length < 1;
  });

  watch(() => props.searchParams, () => {
    collectName.value = '';
  });

  const rules = {
    name: [
      {
        validator: (value: string) => {
          const lastValue = _.find(list.value, item => item.name === value);
          console.log('from validator = ', list, lastValue);
          return !lastValue;
        },
        message: t('条件名称已存在'),
        trigger: 'blue',
      },
    ],
  };

  useRequest(getProfile, {
    onSuccess(data) {
      const profileData = _.find(data.profile, item => item.label === PRIMARY_KEY);
      if (profileData) {
        list.value = profileData.values;
      }
    },
  });

  // 收藏删选条件
  const handleShowForm = () => {
    isShowForm.value = true;
  };

  // 提交收藏
  const handleSubmit = () => {
    isSubmiting.value = true;

    const profileValue = [
      ...list.value,
      {
        name: formData.name,
        params: props.searchParams,
      },
    ];

    formRef.value.validate()
      .then(() => upsertProfile({
        label: PRIMARY_KEY,
        values: profileValue,
      }).then(() => {
        list.value = profileValue;
        isShowForm.value = false;
        collectName.value = formData.name;
      }))
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  // Enter 触发提交
  const handleKeyup = (value: string, event: KeyboardEvent) => {
    if (event.isComposing) {
      // 跳过输入法复合事件
      return;
    }
    if (event.code === 'Enter') {
      handleSubmit();
    }
  };

  // 取消收藏
  const handleCancel = () => {
    isShowForm.value = false;
  };

  // 填充收藏条件
  const handleCollectChange = (value: string) => {
    const result = _.find(list.value, item => item.name === value);
    if (result) {
      emits('change', result.params);
    }
  };

  // 删除收藏条件
  const handleRemove = (payload: { name: string }) => {
    const result = _.filter(list.value, item => item.name !== payload.name);
    if (collectName.value === payload.name) {
      collectName.value = '';
    }
    return upsertProfile({
      label: PRIMARY_KEY,
      values: list.value,
    }).then(() => {
      list.value = result;
    });
  };
</script>
<style lang="less" scoped>
  .collect-serach-params{
    display: inline-flex;
    align-items: center;

    .line{
      display: inline-block;
      width: 1px;
      height: 14px;
      margin: 0 4px 0 8px;
      border: 1px solid #DCDEE5;
    }
  }

  .collect-serach-params-item{
    display: flex;
    align-items: center;

    .remove-btn{
      display: flex;
      height: 18px;
      margin-left: auto;
      font-size: 18px;
      align-items: center;
    }
  }
</style>
