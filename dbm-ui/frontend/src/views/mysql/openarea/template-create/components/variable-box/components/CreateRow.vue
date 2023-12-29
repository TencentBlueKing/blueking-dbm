<template>
  <tbody>
    <td style="padding: 0">
      <TableEditInput
        ref="nameRef"
        v-model="formData.name"
        :rules="nameRules" />
    </td>
    <td style="padding: 0">
      <TableEditInput
        ref="descRef"
        v-model="formData.desc"
        :rules="descRules" />
    </td>
    <td>
      String
    </td>
    <td>
      <BkButton
        :loading="isSubmiting"
        text
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="ml-4"
        text
        theme="primary">
        {{ t('取消') }}
      </BkButton>
    </td>
  </tbody>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateVariable } from '@services/openarea';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { messageSuccess } from '@utils';

  import type { IVariable } from '../Index.vue';

  const emits = defineEmits<{
    'create-change': []
  }>();

  const { t } = useI18n();

  const list = defineModel<IVariable[]>('list', {
    local: true,
    required: true,
  });

  const nameRef = ref<InstanceType<typeof TableEditInput>>();
  const descRef = ref<InstanceType<typeof TableEditInput>>();

  const formData = reactive({
    name: '',
    desc: '',
    builtin: false,
  });

  const nameRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('变量名不能为空'),
    },
    {
      validator: (value: string) => _.every(list.value, item => item.name !== value),
      message: t('变量名重复'),
    },
  ];
  const descRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('变量说明不能为空'),
    },
  ];

  const {
    loading: isSubmiting,
    run: updateVariableMethod,
  } = useRequest(updateVariable<'add'>, {
    manual: true,
    onSuccess() {
      messageSuccess('添加变量成功');
      emits('create-change');
    },
  });

  const handleSubmit = () => {
    Promise.all([
      (nameRef.value as InstanceType<typeof TableEditInput>).getValue(),
      (descRef.value as InstanceType<typeof TableEditInput>).getValue(),
    ]).then(() => {
      updateVariableMethod({
        op_type: 'add',
        new_var: {
          ...formData,
        },
        old_var: undefined,
      });
    });
  };
</script>

