import { reactive } from 'vue';

function useFormModel<T extends object>(initialState: T) {
  const formModel = reactive({ ...initialState }) as T;

  function resetForm() {
    Object.assign(formModel, initialState);
  }

  function setForm(values: Partial<T>) {
    Object.assign(formModel, values);
  }

  return {
    formModel,
    resetForm,
    setForm,
  };
}

export default useFormModel;
