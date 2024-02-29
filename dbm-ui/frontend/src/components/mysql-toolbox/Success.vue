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
  <div class="success">
    <DbIcon
      class="success__icon"
      type="check-line" />
    <p class="success__title">
      <slot>{{ title }}</slot>
    </p>
    <div class="success__desc">
      <slot name="desc">
        <I18nT
          keypath="接下来您可以通过xx查看任务最新动态"
          tag="span">
          <a
            href="javascript:"
            @click="handleGoTicket">
            {{ $t('我的服务单') }}
          </a>
        </I18nT>
      </slot>
    </div>
    <div class="success__steps">
      <div
        v-for="(step, index) in steps"
        :key="index"
        class="step-item">
        <span
          class="step-item__icon"
          :class="`${step.status}`">
          <span class="step-item__status" />
        </span>
        <p class="step-item__title">
          {{ step.title }}
        </p>
      </div>
    </div>
    <div class="success__footers">
      <BkButton
        class="w-88 mr-8"
        theme="primary"
        @click="handleGoTicket">
        {{ $t('去查看') }}
      </BkButton>
      <BkButton
        class="w-88"
        @click="handleGoBack">
        {{ $t('继续提单') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  interface Emits {
    (e: 'close'): void;
  }

  interface Props {
    title: string;
    ticketId: number;
    steps: Array<{ title: string; status?: string }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const router = useRouter();

  function handleGoTicket() {
    const location = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id: props.ticketId,
      },
    });
    window.open(location.href, '_blank');
  }

  function handleGoBack() {
    emits('close');
  }
</script>

<style lang="less" scoped>
  .success {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 8%;

    &__icon {
      display: inline-block;
      width: 64px;
      height: 64px;
      margin-bottom: 36px;
      font-size: 42px;
      line-height: 64px;
      color: white;
      text-align: center;
      background-color: @bg-success;
      border-radius: 50%;
    }

    &__title {
      margin-bottom: 16px;
      font-size: 24px;
      color: @title-color;
    }

    &__desc {
      font-size: @font-size-normal;
    }

    &__steps {
      display: flex;
      margin: 24px 0 32px;

      .step-item {
        position: relative;
        width: 100px;
        overflow: hidden;
        text-align: center;

        &::after {
          position: absolute;
          top: 7px;
          left: 0;
          width: 100%;
          height: 1px;
          background-color: #d8d8d8;
          content: '';
        }

        &:first-child {
          &::after {
            right: 0;
            left: unset;
            width: 50%;
          }
        }

        &:last-child {
          &::after {
            width: 50%;
          }
        }

        &__icon {
          position: relative;
          z-index: 2;
          display: inline-block;
          padding: 0 4px;
          font-size: 0;
          background-color: white;

          .step-item__status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border: 2px solid #d8d8d8;
            border-radius: 50%;
          }

          &.loading {
            .step-item__status {
              position: relative;
              width: 14px;
              height: 14px;
              border-color: @border-primary;

              &::after {
                position: absolute;
                top: 1px;
                left: 1px;
                width: 6px;
                height: 6px;
                border: 1px solid @border-primary;
                border-top-color: white;
                border-radius: 50%;
                content: '';
                animation: success-spin 1.5s linear infinite;
              }
            }
          }
        }

        &__title {
          padding-top: 16px;
        }
      }
    }
  }

  @keyframes success-spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }
</style>
