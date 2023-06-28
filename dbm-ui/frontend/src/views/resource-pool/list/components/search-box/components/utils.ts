export const isValueEmpty = (value: any) => (Array.isArray(value) && value.length < 1)
|| value === '';
