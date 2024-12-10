<template>
  <EditableTable
    ref="table"
    :model="dataModel"
    :rules="rules">
    <EditableTableRow
      v-for="(item, index) in dataModel"
      :key="index">
      <EditableTableColumn
        field="name"
        fixed="left"
        label="第一列"
        :min-width="300"
        :rowspan="5">
        <EditInput
          v-model="item.name"
          clearable
          @clear="handleClear" />
      </EditableTableColumn>
      <EditableTableColumn
        field="age"
        label="第二列"
        :min-width="300"
        required>
        <EditSelect v-model="item.age">
          <BkOption
            id="1"
            name="wx" />
          <BkOption
            id="2"
            name="QQ" />
        </EditSelect>
      </EditableTableColumn>
      <EditableTableColumn
        field="date"
        label="第三列"
        :min-width="300"
        required>
        <EditDatePicker
          v-model="item.date"
          @change="handleChange" />
      </EditableTableColumn>
      <EditableTableColumn
        field="time"
        label="第四列"
        :min-width="300">
        <EditTimePicker
          v-model="item.time"
          @change="handleChange" />
      </EditableTableColumn>
      <EditableTableColumn
        field="tag"
        label="第五列"
        :min-width="300">
        <EditTagInput v-model="item.tag" />
      </EditableTableColumn>
      <EditableTableColumn
        field="tag"
        label="第五列"
        :min-width="300">
        <EditBlock v-model="item.des">
          {{ item.more }}
          <template #append> as </template>
        </EditBlock>
      </EditableTableColumn>
      <EditableTableColumn
        field="more"
        label="第六列"
        :min-width="300">
        <EditTextarea v-model="item.more" />
      </EditableTableColumn>
    </EditableTableRow>
  </EditableTable>
  <BkButton
    :loading="isSubmiting"
    @click="handleSubmit">
    提交
  </BkButton>
</template>
<script setup lang="ts">
  import { reactive, useTemplateRef } from 'vue';

  import EditableTable, {
    Block as EditBlock,
    Column as EditableTableColumn,
    DatePicker as EditDatePicker,
    Input as EditInput,
    Row as EditableTableRow,
    Select as EditSelect,
    TagInput as EditTagInput,
    Textarea as EditTextarea,
    TimePicker as EditTimePicker,
  } from '@components/editable-table/Index.vue';

  const createData = () => ({
    name: 'name',
    age: '',
    date: '',
    time: '',
    tag: [],
    des: '这是一段描述文字',
    more: 'mormeroemroemroemro',
  });

  const tableRef = useTemplateRef('table');
  const isSubmiting = ref(false);
  const isLoading = ref(true);

  setTimeout(() => {
    isLoading.value = false;
  }, 10000);

  const dataModel = reactive([
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
    createData(),
  ]);

  const rules = {
    name: [
      {
        validator: (value: string) => {
          console.log('name = ', value);
          return Boolean(value);
        },
        message: '错了',
        trigger: 'blur',
      },
    ],
    age: [
      {
        validator: (value: string) => {
          console.log('validator', value);
          return true;
        },
        message: '错了没',
        trigger: 'change',
      },
    ],
  };

  const handleClear = () => {
    console.log('handleClear');
  };

  const handleChange = (value: string) => {
    console.log(value);
  };

  const handleSubmit = () => {
    isSubmiting.value = true;
    tableRef
      .value!.validate()
      .then(() => {
        console.log('success');
      })
      .finally(() => {
        console.log('finally');
        isSubmiting.value = false;
      });
  };
</script>
