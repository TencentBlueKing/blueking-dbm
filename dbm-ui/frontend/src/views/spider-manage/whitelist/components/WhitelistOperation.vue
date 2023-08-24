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
    :esc-close="false"
    :is-show="isShow"
    :quick-close="false"
    :title="title"
    :width="640"
    @closed="handleCancel">
    <DbForm
      ref="formRef"
      class="mb-20"
      form-type="vertical"
      :model="formdata">
      <BkFormItem
        ref="ipRef"
        :label="t('IP地址')"
        property="ips"
        required
        :rules="ipRules">
        <BkInput
          v-model="formdata.ips"
          :placeholder="t('白名单输入框编辑提示')"
          style="height: 134px;"
          type="textarea"
          @input="debounceInput" />
        <!-- <template #error="error">
          <div class="error-slot">
            <span>{{ error }}</span>
            <BkButton
              v-if="formdata.ips !== ''"
              class="error-slot-btn"
              text
              @click="handleDelete">
              <Del
                height="14"
                width="14" />
            </BkButton>
          </div>
        </template> -->
      </BkFormItem>
      <BkFormItem
        :label="t('备注')"
        property="remark"
        required>
        <BkInput
          v-model="formdata.remark"
          :maxlength="100"
          :placeholder="t('请添加IP的简要说明_如IP用途等')"
          style="height: 114px;"
          type="textarea" />
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
  <div style="display: none;">
    <div
      ref="mergeTipsRef"
      class="merge-tips"
      style=" padding: 4px; font-size: 12px;color: #63656e;">
      <p class="pb-12">
        {{ t('检测到多个前缀相同的IP_是否立即合并成以下IP') }}
      </p>
      <p
        v-for="ip in mergeValues"
        :key="ip">
        {{ ip }}
      </p>
      <div class="pt-12">
        <BkButton
          text
          theme="primary"
          @click="handleMerge">
          {{ t("合并") }}
        </BkButton>
        <span
          class="inline-block"
          style="transform: scale(0.8);">｜</span>
        <BkButton
          text
          theme="primary"
          @click="handleNoMerge">
          {{ t('不合并') }}
        </BkButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import type { WhitelistItem } from '@services/types/whitelist';
  import {
    createWhitelist,
    updateWhitelist,
  } from '@services/whitelist';

  import { ClusterTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import { messageSuccess } from '@utils';

  interface Props {
    title: string,
    bizId: number,
    isEdit: boolean,
    data: WhitelistItem
  }

  interface Emits {
    (e: 'successed'): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({} as WhitelistItem),
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();

  const replaceReg = /[,;\r\n]/g;
  const ipSegmentMax = 255;
  const ipSegmentMin = 0;
  const formRef = ref();
  const mergeTipsRef = ref();
  const ipRef = ref();
  const formdata = reactive({
    ips: '',
    remark: '',
  });
  const isSubmitting = ref(false);
  let mergeInst: Instance | undefined = undefined;
  const renderValues = ref<string[]>([]);
  const mergeValues = ref<string[]>([]);
  const ignoreValues = ref<string[]>([]);

  // 判断是否为合法的 ip 段，即 nnn.nnn.nnn.nnn 中 0 <= nnn <= 255
  const isLegalSegment = (segment: string) => {
    const seg = Number(segment);

    // 存在非数字
    if (!Number.isFinite(seg)) return false;
    // 存在 001 类似情况
    if (segment.length !== String(seg).length) return false;

    return seg >= ipSegmentMin && seg <= ipSegmentMax;
  };

  const validateWildcard = (text: string): boolean => {
    // 允许直接填写单个 %
    if (text === '%') return true;
    // % 符号必须放最后
    if (!text.endsWith('%')) return false;

    const segments = text.slice(0, -1).split('.');
    const lastSegment = segments.slice(-1)[0];
    // ip 分段最多4个
    if (segments.length > 4) return false;

    // 最后分段为空也允许
    return segments.slice(0, -1).every(segment => isLegalSegment(segment))
      && (lastSegment === '' || isLegalSegment(lastSegment));
  };

  // const validateRange = (text: string): boolean => {
  //   const ipArr = text.split('~');

  //   if (ipArr.length !== 2) return false;

  //   const [ip, end] = ipArr;

  //   return ipv4.test(ip) && (ip.split('.').pop() || 0) < end && isLegalSegment(end);
  // };

  const ipRules = [
    {
      validator: (value: string) => value
        .replace(replaceReg, ',')
        .split(',')
        .every((ip) => {
          console.log(ip);
          if (!ip.includes('%')) return ipv4.test(ip.trim());
          return true;
        }),
      message: t('IP格式错误'),
      trigger: 'blur',
    },
    {
      validator: (value: string) => value
        .replace(replaceReg, ',')
        .split(',')
        .every((ip) => {
          // 包含 % 字符
          if (ip.includes('%')) return validateWildcard(ip.trim());
          return true;
        }),
      message: t('ip匹配_中存在格式错误'),
      trigger: 'blur',
    },
    // {
    //   validator: (value: string) => value
    //     .replace(replaceReg, ',')
    //     .split(',')
    //     // 包含 ~ 字符
    //     .filter(text => text.includes('~'))
    //     .map(text => text.trim())
    //     .every(text => validateRange(text)),
    //   message: t('ip 范围段(~)中存在格式错误'),
    //   trigger: 'blur',
    // },
  ];

  watch(isShow, (isShow) => {
    if (isShow && props.isEdit) {
      formdata.remark = props.data.remark;
      formdata.ips = props.data.ips.join('\n');
    }
  }, { immediate: true });

  const renderTips = () => {
    handleHideMergeInst();

    if (mergeTipsRef.value && ipRef.value.$el) {
      mergeInst = tippy(ipRef.value.$el as SingleTarget, {
        content: mergeTipsRef.value,
        placement: 'left',
        appendTo: 'parent',
        theme: 'light',
        maxWidth: 'none',
        trigger: 'manual',
        interactive: true,
        arrow: true,
        offset: [0, 8],
        zIndex: 999999,
        hideOnClick: false,
      });

      mergeInst.show();
    }
  };

  // 没有达到数量的 IP 不进行合并
  const resolveMergeIpMap = (ipMap: Map<string, string[]>, ips: string[], limit = 2) => {
    const entries = ipMap.entries();
    for (const [ip, values] of entries) {
      if (values.length <= limit) {
        ips.push(...values);
        ipMap.delete(ip);
      }
    }
  };

  const debounceInput = _.debounce((value: string) => {
    mergeValues.value = [];
    renderValues.value = [];

    const ips = value.split('\n').filter(ip => ip.trim());
    // 记录相同 aaa.bbb.ccc.% 的 ip
    const abcIpMap = new Map<string, string[]>();
    for (const ip of ips) {
      // 不通过 ip 校验的则直接回填，不修改用户内容
      if (!ipv4.test(ip)) {
        renderValues.value.push(ip);
        continue;
      }

      // 修改为 aaa.bbb.ccc.%
      const abcIp = `${ip.slice(0, ip.lastIndexOf('.'))}.%`;
      // 修改为 aaa.bbb.%
      const abIp = `${abcIp.slice(0, abcIp.slice(0, -2).lastIndexOf('.'))}.%`;
      // 处理上次忽略合并的 IP
      if (ignoreValues.value.includes(abcIp) || ignoreValues.value.includes(abIp)) {
        renderValues.value.push(ip);
        continue;
      }
      abcIpMap.set(abcIp, (abcIpMap.get(abcIp) || []).concat([ip]));
    }
    resolveMergeIpMap(abcIpMap, renderValues.value);

    // 记录相同 aaa.bbb.% 的 ip
    const abIpMap = new Map<string, string[]>();
    for (const abcIp of abcIpMap.keys()) {
      // 修改为 aaa.bbb.%
      const abIp = `${abcIp.slice(0, abcIp.slice(0, -2).lastIndexOf('.'))}.%`;
      abIpMap.set(abIp, (abIpMap.get(abIp) || []).concat([abcIp]));
    }
    resolveMergeIpMap(abIpMap, mergeValues.value);

    // 区分 aaa.bbb.ccc.% 与 aaa.bbb.%
    for (const [ip, values] of abIpMap.entries()) {
      // 不需要进一步合并
      if (value.length <= 2) {
        mergeValues.value.push(...values);
        continue;
      }
      mergeValues.value.push(ip);
    }

    if (mergeValues.value.length > 0) {
      renderTips();
    }
  }, 200);

  const handleHideMergeInst = () => {
    if (mergeInst) {
      mergeInst.hide();
      mergeInst.unmount();
      mergeInst.destroy();
      mergeInst = undefined;
    }
  };

  const handleNoMerge = () => {
    ignoreValues.value.push(...mergeValues.value);
    handleHideMergeInst();
  };

  const handleMerge = () => {
    formdata.ips = [...renderValues.value, ...mergeValues.value].join('\n');
    handleHideMergeInst();
  };

  // const handleDelete = () => {
  //   const { ips } = formdata;

  //   const regex = /(?:[^,;\r\n]+[,\r\n;]?)/g;
  //   const ipArr = ips.match(regex);
  //   const length = ipArr?.length || 0;

  //   const filterIps = ipArr?.filter((ip: string, index: number) => {
  //     let ipValidating = ip.trim();

  //     if (index < length - 1) {
  //       ipValidating = ipValidating.replace(replaceReg, '');
  //     }

  //     if (ipv4.test(ipValidating) || ipv6.test(ipValidating)) {
  //       return true;
  //     }

  //     if (ipValidating.includes('%')) {
  //       return validateWildcard(ipValidating);
  //     }

  //     if (ipValidating.includes('~')) {
  //       return validateRange(ipValidating);
  //     }

  //     return false;
  //   });

  //   formdata.ips = filterIps?.join('') || '';
  // };

  const handleCancel = () => {
    isShow.value = false;
    formRef.value.clearValidate();
    window.changeConfirm = false;

    setTimeout(() => {
      formdata.ips = '';
      formdata.remark = '';
      renderValues.value = [];
      mergeValues.value = [];
      ignoreValues.value = [];
    }, 300);
  };

  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        isSubmitting.value = true;
        const api = props.isEdit ? updateWhitelist : createWhitelist;

        api({
          ips: formdata.ips
            .replace(replaceReg, '\n')
            .split('\n')
            .filter(ip => ip !== ''),
          remark: formdata.remark,
          bk_biz_id: props.bizId,
          id: props.data?.id || 0,
          db_type: ClusterTypes.TENDBCLUSTER,
        })
          .then(() => {
            messageSuccess(t('创建成功'));
            handleCancel();
            emits('successed');
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      });
  };
</script>

<style scoped lang="less">
.error-slot {
  display: flex;
}

.error-slot-btn {
  margin-left: 4px;
}
</style>
