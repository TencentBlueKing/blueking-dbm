const statusModule = Object.values(
  import.meta.glob<{
    default: {
      name: string;
    };
  }>('./*.vue', {
    eager: true,
  }),
).reduce<Record<string, Record<string, string>>>(
  (result, item) =>
    Object.assign(result, {
      [item.default.name]: item.default,
    }),
  {},
);

export default statusModule;
