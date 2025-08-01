import { getFileContent } from '@services/source/storage';

import { useSqlImport } from '@stores';

import SqlFileModel from '@views/db-manage/common/mysql-sql-execute/model/SqlFile';

import { getSQLFilename } from '@utils';

export default () => {
  const sqlImportStore = useSqlImport();

  const selectFileName = ref('');
  const isContentLoading = ref(false); // 回显
  const fileNameList = shallowRef<Array<string>>([]);
  const fileDataMap = ref<Record<string, SqlFileModel>>({});

  // 当前选择文件数据
  const selectFileData = computed(() => fileDataMap.value[selectFileName.value]);

  const fetchFileContentByFileName = (fileName: string) => {
    const uploadFilePath = sqlImportStore.uploadFilePath;
    if (!uploadFilePath) {
      return;
    }
    isContentLoading.value = true;
    getFileContent({
      file_path: `${uploadFilePath}/${fileName}`,
    })
      .then((data) => {
        const sqlFileName = getSQLFilename(fileName);
        const fileInfo = fileDataMap.value[sqlFileName];
        if (fileInfo) {
          fileDataMap.value[sqlFileName].content = data.content;
        }
      })
      .finally(() => {
        isContentLoading.value = false;
      });
  };

  watch(
    selectFileName,
    () => {
      // 重新编辑状态不需要 SQL 文件检测，需要异步获取文件内容
      if (
        !selectFileName.value ||
        fileDataMap.value[selectFileName.value].content ||
        fileDataMap.value[selectFileName.value].state === SqlFileModel.CHECKING ||
        !fileDataMap.value[selectFileName.value].grammarCheck
      ) {
        return;
      }

      fetchFileContentByFileName(fileDataMap.value[selectFileName.value].realFilePath);
    },
    {
      immediate: true,
    },
  );

  return {
    fetchFileContentByFileName,
    fileDataMap,
    fileNameList,
    isContentLoading,
    selectFileData,
    selectFileName,
  };
};
