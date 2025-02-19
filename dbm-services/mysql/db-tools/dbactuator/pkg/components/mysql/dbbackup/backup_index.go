package dbbackup

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/backupexe"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"

	"github.com/pkg/errors"
)

// BackupIndexFile godoc
type BackupIndexFile struct {
	dbareport.IndexContent

	indexFilePath string
	// backupFiles {data: {file1: obj, file2: obj}, priv: {}}
	backupFiles map[string][]dbareport.TarFileItem
	// 备份文件解压后的目录名，相对目录
	backupIndexBasename string
	// 备份文件的所在根目录，比如 /data/dbbak
	backupDir string
	// targetDir 备份解压后的目录，比如 /data/dbbak/xxx/20000/<backupIndexBasename>/
	targetDir       string
	tarfileBasename string
	splitParts      []string
	tarParts        []string
}

// ParseBackupIndexFile read index file: fileDir/fileName
func ParseBackupIndexFile(indexFilePath string, indexObj *BackupIndexFile) error {
	fileDir, fileName := filepath.Split(indexFilePath)
	bodyBytes, err := os.ReadFile(indexFilePath)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(bodyBytes, indexObj); err != nil {
		logger.Error("fail to read index file to struct: %s, err:%s", fileName, err.Error())
		return err
	}

	indexObj.indexFilePath = indexFilePath
	indexObj.backupIndexBasename = strings.TrimSuffix(fileName, ".index")
	indexObj.backupDir = fileDir

	indexObj.backupFiles = make(map[string][]dbareport.TarFileItem)
	for _, fileItem := range indexObj.FileList {
		indexObj.backupFiles[fileItem.FileType] = append(indexObj.backupFiles[fileItem.FileType], *fileItem)
	}
	logger.Info("backupIndexBasename=%s, backupType=%s, charset=%s",
		indexObj.backupIndexBasename, indexObj.BackupType, indexObj.BackupCharset)
	return indexObj.ValidateFiles()
}

// GetTarFileList 从 index 中返回文件名列表
// fileType="" 时返回所有
func (f *BackupIndexFile) GetTarFileList(fileType string) []string {
	fileNamelist := []string{}
	if fileType == "" {
		for _, fileItem := range f.FileList {
			fileNamelist = append(fileNamelist, fileItem.FileName)
		}
		return util.UniqueStrings(fileNamelist)
	} else {
		fileList := f.backupFiles[fileType]
		for _, f := range fileList {
			fileNamelist = append(fileNamelist, f.FileName)
		}
		return util.UniqueStrings(fileNamelist)
	}
}

// ValidateFiles 校验文件是否连续，文件是否存在，文件大小是否正确
// splitParts example:  [a.part_1, a.part_2]
// tarParts example:  [a.0.tar  a.1.tar]
func (f *BackupIndexFile) ValidateFiles() error {
	var errFiles []string
	reSplitPart := regexp.MustCompile(dbareport.ReSplitPart)
	reTarPart := regexp.MustCompile(dbareport.ReTar) // 如果只有一个tar，也会存到这里
	tarPartsWithoutSuffix := []string{}              // remove .tar suffix from tar to get no. sequence
	for _, tarFile := range f.FileList {
		if fSize := cmutil.GetFileSize(filepath.Join(f.backupDir, tarFile.FileName)); fSize < 0 {
			errFiles = append(errFiles, tarFile.FileName)
			continue
		} // else if fSize != tarFile.TarFileSize {}
		if reSplitPart.MatchString(tarFile.FileName) {
			f.splitParts = append(f.splitParts, tarFile.FileName)
		} else if reTarPart.MatchString(tarFile.FileName) {
			tarPartsWithoutSuffix = append(tarPartsWithoutSuffix, strings.TrimSuffix(tarFile.FileName, ".tar"))
			f.tarParts = append(f.tarParts, tarFile.FileName)
		}
		tarfileBasename := backupexe.ParseTarFilename(tarFile.FileName)
		if tarfileBasename != "" && f.tarfileBasename == "" {
			f.tarfileBasename = tarfileBasename
		} else if tarfileBasename != "" && f.tarfileBasename != tarfileBasename {
			return errors.Errorf("tar file base name error: %s, file:%s", f.tarfileBasename, tarFile.FileName)
		}
	}
	if len(errFiles) != 0 {
		return errors.Errorf("files not found in %s: %v", f.backupDir, errFiles)
	}
	if f.tarfileBasename != f.backupIndexBasename {
		// logger index baseName nad tarfile baseName does not match
	}
	sort.Strings(f.splitParts)
	f.splitParts = util.SortSplitPartFiles(f.splitParts, "_")

	sort.Strings(f.tarParts)

	if len(f.splitParts) >= 2 { // 校验文件是否连续
		fileSeqList := util.GetSuffixWithLenAndSep(f.splitParts, "_", 0)
		if _, err := util.IsConsecutiveStrings(fileSeqList, true); err != nil {
			return err
		}
	}
	if len(tarPartsWithoutSuffix) >= 2 {
		fileSeqList := util.GetSuffixWithLenAndSep(tarPartsWithoutSuffix, "_", 0)
		if _, err := util.IsConsecutiveStrings(fileSeqList, true); err != nil {
			return err
		}
	}
	return nil
}

// UntarFiles merge and untar
// set targetDir
func (f *BackupIndexFile) UntarFiles(untarDir string, removeOriginal bool) error {
	if untarDir == "" {
		return errors.Errorf("untar target dir should not be emtpy")
	}

	if cmutil.FileExists(f.targetDir) {
		return errors.Errorf("target untar path already exists %s", f.targetDir)
	}

	// 物理备份, merge parts
	if len(f.splitParts) > 0 && len(f.splitParts) <= 20 {
		// TODO 考虑使用 pv 限速
		cmd := fmt.Sprintf(`cd %s && cat %s | tar -xf - -C %s/`,
			f.backupDir, strings.Join(f.splitParts, " "), untarDir)
		if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
			return errors.Wrap(err, cmd)
		}
	} else if len(f.splitParts) > 20 {
		if err := MergeAndUntarFiles(f.splitParts, f.backupDir, untarDir, true); err != nil {
			return err
		}
	}

	if len(f.tarParts) > 0 {
		for _, p := range f.tarParts {
			backupexe.ParseTarFilename(p)
			cmd := fmt.Sprintf(`cd %s && tar -xf %s -C %s/`, f.backupDir, p, untarDir)
			if strings.Contains(p, ".gz") {
				cmd = fmt.Sprintf(`cd %s && cat %s | tar -zxf - -C %s/`,
					f.backupDir, strings.Join(f.tarParts, " "), untarDir)
			}
			if _, err := osutil.ExecShellCommand(false, cmd); err != nil {
				return errors.Wrap(err, cmd)
			}
			if removeOriginal {
				logger.Info("remove original file %s", p)
				os.Remove(p)
			}
		}
	}

	if !cmutil.FileExists(f.targetDir) {
		return errors.Errorf("targetDir %s is not ready", f.targetDir)
	}
	return nil
}

// MergeAndUntarFiles 当文件数非常多时，避免超过命令行长度
// 单个文件解压
// removeOriginal 为 true 时，会清理原文件
func MergeAndUntarFiles(splitParts []string, srcDir, untarDir string, removeOriginal bool) error {
	pipeReader, pipeWriter := io.Pipe()
	untarCmd := exec.Command("tar", "-xf", "-", "-C", untarDir)
	if strings.Contains(splitParts[0], ".gz") {
		untarCmd = exec.Command("tar", "-zxf", "-", "-C", untarDir)
	}
	var stderrBuff bytes.Buffer
	untarCmd.Stderr = &stderrBuff
	untarCmd.Stdin = pipeReader
	untarCmd.Dir = srcDir
	errChan := make(chan error, 2) // read and write 共用，避免 hang 住，所以给 2 个
	go func() {
		cmdErr := untarCmd.Run()
		if cmdErr != nil {
			cmdErr = errors.Wrapf(cmdErr, "%s: %s", stderrBuff.String(), untarCmd.String())
			// 这里要关闭 pipeWriter，不然后面的 io.Copy 可能会阻塞
			pipeWriter.CloseWithError(cmdErr)
		}
		errChan <- cmdErr
		return
	}()

	go func() {
		var readErr error
		for _, tarFile := range splitParts {
			logger.Info("read file %s", tarFile)
			tarFile = filepath.Join(srcDir, tarFile)
			tarf, err := os.OpenFile(tarFile, os.O_RDONLY, 0644)
			if err != nil {
				readErr = errors.WithMessage(err, "read file")
				errChan <- readErr
				// 任何错误，都传输给 pipeWriter，以便管道下游命令能够捕获 error
				break
			}
			if _, err = io.Copy(pipeWriter, tarf); err != nil {
				readErr = errors.WithMessage(err, "copy file to stdout")
				errChan <- readErr
				break
			}
			tarf.Close()
			if removeOriginal {
				logger.Info("remove backup file %s", tarFile)
				os.Remove(tarFile)
			}
		}
		pipeWriter.CloseWithError(readErr)
	}()

	select {
	case err := <-errChan:
		if err != nil {
			return err
		}
	}
	if errStr := stderrBuff.String(); strings.TrimSpace(errStr) != "" {
		return errors.New(errStr)
	}
	return nil
}

// GetTargetDir 返回解压后的目录
// 考虑到某些情况 backupIndexBasename.index 跟 tar file name 可能不同
// 需在调用 ValidateFiles() 之后才有效
func (f *BackupIndexFile) GetTargetDir(untarDir string) string {
	if f.tarfileBasename != "" {
		// logger index baseName nad tarfile baseName does not match
		f.targetDir = filepath.Join(untarDir, f.tarfileBasename)
	} else {
		f.targetDir = filepath.Join(untarDir, f.backupIndexBasename)
	}
	return f.targetDir
}

func (f *BackupIndexFile) GetMetafileBasename() string {
	return f.backupIndexBasename
}

func ExtractTarGz(gzipStream io.Reader) error {
	uncompressedStream, err := gzip.NewReader(gzipStream)
	if err != nil {
		return errors.New("ExtractTarGz: NewReader failed")
	}

	tarReader := tar.NewReader(uncompressedStream)

	for true {
		header, err := tarReader.Next()

		if err == io.EOF {
			break
		}

		if err != nil {
			return errors.Wrap(err, "ExtractTarGz: Next() failed")
		}

		switch header.Typeflag {
		case tar.TypeDir:
			if err := os.Mkdir(header.Name, 0755); err != nil {
				return errors.Wrap(err, "ExtractTarGz: Mkdir() failed")

			}
		case tar.TypeReg:
			outFile, err := os.Create(header.Name)
			if err != nil {
				return errors.Wrap(err, "ExtractTarGz: Create() failed")
			}
			if _, err := io.Copy(outFile, tarReader); err != nil {
				return errors.Wrap(err, "ExtractTarGz: Copy() failed")

			}
			outFile.Close()

		default:
			return errors.Errorf("ExtractTarGz: uknown type: %s in %s",
				header.Typeflag,
				header.Name)
		}
	}
	return nil
}
