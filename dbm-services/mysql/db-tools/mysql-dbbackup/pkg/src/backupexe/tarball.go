package backupexe

import (
	"archive/tar"
	"fmt"
	"io"
	"io/fs"
	"math"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strings"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// PackageFile package backup files
type PackageFile struct {
	// srcDir 计划的打包目录 /data/dbbak/x_xxx_xxx
	srcDir string
	// dstDir 打包的目标目录
	dstDir     string
	dstTarFile string
	cnf        *config.BackupConfig
	indexFile  *dbareport.IndexContent
}

// MappingPackage Package multiple backup files
// sort file list
// traverse file list
// create new tar_writer
// write file to tar package
// calculate the sums of file size, compare it with size limit
// create new tar_writer
// loop ...
// write last file to tar package
// will save index meta info to file
func (p *PackageFile) MappingPackage() error {
	logger.Log.Infof("Tarball Package: src dir %s, iolimit %d MB/s", p.srcDir, p.cnf.Public.IOLimitMBPerSec)

	var tarSize uint64 = 0
	tarFileNum := 0
	var tarUtil = util.TarWriter{IOLimitMB: p.cnf.Public.IOLimitMBPerSec}
	var dstTarName = fmt.Sprintf(`%s_%d.tar`, p.dstDir, tarFileNum)
	if p.cnf.Public.EncryptOpt.EncryptEnable {
		logger.Log.Infof("tar file encrypt enabled for port: %d", p.cnf.Public.MysqlPort)
		tarUtil.Encrypt = true
		tarUtil.EncryptTool = p.cnf.Public.EncryptOpt.GetEncryptTool()
		dstTarName = fmt.Sprintf(`%s_%d.tar.%s`, p.dstDir, tarFileNum, tarUtil.EncryptTool.DefaultSuffix())
	}

	if err := tarUtil.New(dstTarName); err != nil {
		return err
	}
	defer func() {
		_ = tarUtil.Close() // the last tar file to close
	}()

	var totalSizeUncompress int64 = 0 // -1 means does not calculate size before compress
	var backupTotalFileSize uint64
	tarSizeMaxBytes := p.cnf.Public.TarSizeThreshold * 1024 * 1024
	// 把 schema 单独打包？

	var tarFiles = make(map[string]*dbareport.TarFileItem, 0)
	// The files are walked in lexical order
	walkErr := filepath.Walk(p.srcDir, func(filename string, info fs.FileInfo, err error) error {
		if err != nil {
			return err
		}
		header, err := tar.FileInfoHeader(info, "")
		if err != nil {
			return err
		}
		header.Name = filepath.Join(p.cnf.Public.TargetName(), strings.TrimPrefix(filename, p.srcDir))

		isFile, written, err := tarUtil.WriteTar(header, filename)
		if err != nil {
			return err
		} else if !isFile {
			return nil
		}
		tarFileName := filepath.Base(dstTarName)
		if _, ok := tarFiles[tarFileName]; !ok {
			tarFiles[tarFileName] = &dbareport.TarFileItem{FileName: tarFileName, FileType: cst.FileTar}
		} else {
			tarFiles[tarFileName].ContainFiles = append(tarFiles[tarFileName].ContainFiles,
				strings.TrimPrefix(strings.TrimPrefix(filename, p.srcDir), "/"))
		}
		tarFiles[tarFileName].FileSize += written

		if totalSizeUncompress > -1 && strings.HasSuffix(filename, cst.ZstdSuffix) {
			if sizeUncompress, err := readUncompressSizeForZstd(CmdZstd, filename); err != nil {
				logger.Log.Warnf("fail to readUncompressSizeForZstd for file %s, err: %s", filename, err.Error())
				totalSizeUncompress = -1
			} else {
				totalSizeUncompress += sizeUncompress
			}
		}
		if err = os.Remove(filename); err != nil { //TODO 限速？
			logger.Log.Error("failed to remove file while taring, err:", err)
		}

		tarSize += uint64(written)
		if tarSize >= tarSizeMaxBytes {
			logger.Log.Infof("need to tar file, accumulated tar size: %d bytes, dstFile: %s", tarSize, dstTarName)
			backupTotalFileSize += tarSize
			tarSize = 0
			tarFileNum++
			if err = tarUtil.Close(); err != nil {
				return err
			}
			// new tarUtil object will be used for next loop
			dstTarName = fmt.Sprintf(`%s_%d.tar`, p.dstDir, tarFileNum)
			if p.cnf.Public.EncryptOpt.EncryptEnable {
				dstTarName = fmt.Sprintf(`%s_%d.tar.%s`, p.dstDir, tarFileNum, tarUtil.EncryptTool.DefaultSuffix())
			}
			if err = tarUtil.New(dstTarName); err != nil {
				return err
			}
		}
		return nil
	})
	if walkErr != nil {
		logger.Log.Error("walk dir, err: ", walkErr)
		return walkErr
	}
	logger.Log.Infof("need to tar file, accumulated tar size: %d bytes, dstFile: %s", tarSize, dstTarName)
	p.indexFile.TotalSizeKBUncompress = totalSizeUncompress / 1024
	p.indexFile.TotalFilesize = backupTotalFileSize + tarSize

	logger.Log.Infof("old srcDir removing io is limited to: %d MB/s", p.cnf.Public.IOLimitMBPerSec)
	if err := cmutil.TruncateDir(p.srcDir, p.cnf.Public.IOLimitMBPerSec); err != nil {
		// if err := os.RemoveAll(p.srcDir); err != nil {
		logger.Log.Error("failed to remove useless backup files")
		return err
	}
	for _, tarFile := range tarFiles {
		p.indexFile.FileList = append(p.indexFile.FileList, tarFile)
	}
	p.indexFile.AddPrivFileItem(p.dstDir)
	if _, err := p.indexFile.SaveIndexContent(&p.cnf.Public); err != nil {
		return err
	}
	return nil
}

// SplittingPackage Firstly, put all backup files into the tar file. Secondly, split the tar file to multiple parts
// will save index meta info to file
func (p *PackageFile) SplittingPackage() error {
	// tar srcDir to tar
	if err := p.tarballDir(); err != nil {
		return err
	}
	if fileSize := cmutil.GetFileSize(p.dstTarFile); fileSize >= 0 {
		p.indexFile.TotalFilesize = uint64(fileSize)
	} else {
		return errors.Errorf("fail to get file size for %s, got %d", p.dstTarFile, fileSize)
	}

	// split tar file to parts
	if err := p.splitTarFile(p.dstTarFile); err != nil {
		return err
	}

	p.indexFile.AddPrivFileItem(p.dstDir)
	if _, err := p.indexFile.SaveIndexContent(&p.cnf.Public); err != nil {
		return err
	}
	return nil
}

// tarballDir tar srcDir to dstTarFile
// remove srcDir if success
func (p *PackageFile) tarballDir() error {
	logger.Log.Infof("Tarball Package: src dir %s, iolimit %d MB/s", p.srcDir, p.cnf.Public.IOLimitMBPerSec)
	var tarUtil = util.TarWriter{IOLimitMB: p.cnf.Public.IOLimitMBPerSec}
	if err := tarUtil.New(p.dstTarFile); err != nil {
		return err
	}
	defer func() {
		_ = tarUtil.Close()
	}()

	var totalSizeUncompress int64 = 0
	walkErr := filepath.Walk(p.srcDir, func(filename string, info fs.FileInfo, err error) error {
		if err != nil {
			return err
		}
		header, err := tar.FileInfoHeader(info, "")
		if err != nil {
			return err
		}
		header.Name = filepath.Join(p.cnf.Public.TargetName(), strings.TrimPrefix(filename, p.srcDir))
		isFile, _, err := tarUtil.WriteTar(header, filename)
		if err != nil {
			return err
		} else if !isFile {
			return nil
		}
		if totalSizeUncompress > -1 && strings.HasSuffix(filename, cst.ZstdSuffix) {
			if sizeUncompress, err := readUncompressSizeForZstd(CmdZstd, filename); err != nil {
				logger.Log.Warnf("fail to readUncompressSizeForZstd for file %s, err: %s", filename, err.Error())
				totalSizeUncompress = -1
			} else {
				totalSizeUncompress += sizeUncompress
			}
		}

		// TODO limit io rate when removing
		if err = os.Remove(filename); err != nil {
			logger.Log.Error("failed to remove file while taring, err:", err)
		}

		return nil
	})
	if walkErr != nil {
		return walkErr
	}
	if err := os.RemoveAll(p.srcDir); err != nil {
		return err
	}
	return nil
}

// splitTarFile split Tar file into multiple part_file
// update indexFile
// destFile has is full path file
func (p *PackageFile) splitTarFile(destFile string) error {
	splitSpeed := int64(300) // default: 300MB/s
	if p.cnf.PhysicalBackup.SplitSpeed != 0 {
		splitSpeed = p.cnf.PhysicalBackup.SplitSpeed
	}
	logger.Log.Infof("Splitting Package: Tar file %s with iolimit %d MB/s", p.dstTarFile, splitSpeed)
	fileInfo, err := os.Stat(destFile)
	if err != nil {
		logger.Log.Error(fmt.Sprintf("stat %s, err :%v", destFile, err))
		return err
	}
	filePartSize := int64(p.cnf.Public.TarSizeThreshold) * 1024 * 1024 // MB to bytes
	partNum := int(math.Ceil(float64(fileInfo.Size()) / float64(filePartSize)))
	if partNum == 1 {
		p.indexFile.FileList = append(p.indexFile.FileList, &dbareport.TarFileItem{
			FileName: filepath.Base(destFile),
			FileSize: fileInfo.Size(),
			FileType: cst.FileTar,
		})
		return nil
	}

	// num >=1
	fi, err := os.OpenFile(destFile, os.O_RDONLY, os.ModePerm)
	if err != nil {
		logger.Log.Error(fmt.Sprintf("open file %s, err :%v", destFile, err))
		return err
	}
	defer func() {
		_ = fi.Close()
	}()

	paddingSize := len(cast.ToString(partNum))
	for i := 0; i < partNum; i++ {
		dstTarName := strings.TrimSuffix(destFile, ".tar")
		partTarName := fmt.Sprintf(`%s.part_%0*d`, dstTarName, paddingSize, i) // ReSplitPart
		destFileWriter, err := os.OpenFile(partTarName, os.O_CREATE|os.O_WRONLY, os.ModePerm)
		if err != nil {
			return err
		}
		// io.Copy will record fi Seek Position
		if written, err := cmutil.IOLimitRateWithChunk(destFileWriter, fi, splitSpeed, filePartSize); err == nil {
			_ = destFileWriter.Close()
			p.indexFile.FileList = append(p.indexFile.FileList, &dbareport.TarFileItem{
				FileName: filepath.Base(partTarName),
				FileSize: written,
				FileType: cst.FilePart,
			})
		} else {
			_ = destFileWriter.Close()
			if err == io.EOF { // read end
				p.indexFile.FileList = append(p.indexFile.FileList, &dbareport.TarFileItem{
					FileName: filepath.Base(partTarName),
					FileSize: written,
					FileType: cst.FilePart,
				})
				break
			}
			return err
		}
	}
	// remove old tar File
	logger.Log.Infof("old tar removing io is limited to: %d MB/s", p.cnf.Public.IOLimitMBPerSec)
	if err := cmutil.TruncateFile(p.dstTarFile, p.cnf.Public.IOLimitMBPerSec); err != nil {
		return err
	}
	return nil
}

// PackageBackupFiles package backup files
// backupReport 里面还只有 base 信息，没有文件信息
func PackageBackupFiles(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent) error {
	targetDir := path.Join(cnf.Public.BackupDir, cnf.Public.TargetName())
	var packageFile = &PackageFile{
		srcDir:     targetDir,
		dstDir:     targetDir,
		dstTarFile: targetDir + ".tar",
		cnf:        cnf,
		indexFile:  metaInfo,
	}
	logger.Log.Infof("Index BackupMetaInfo:%+v", metaInfo)

	// package files, and produce the index file at the same time
	if strings.ToLower(cnf.Public.BackupType) == cst.BackupLogical {
		if err := packageFile.MappingPackage(); err != nil {
			return err
		}
	} else if strings.ToLower(cnf.Public.BackupType) == cst.BackupPhysical {
		if err := packageFile.SplittingPackage(); err != nil {
			return err
		}
	}
	return nil
}

// readUncompressSizeForZstd godoc
// Frames  Skips  Compressed  Uncompressed  Ratio  Check  Filename
//
//	1      0     187 MiB      1.20 GiB  6.606  XXH64  mysqldata.tar.zst
func readUncompressSizeForZstd(zstdCmd string, fileName string) (int64, error) {
	outStr, _, err := cmutil.ExecCommand(false, "", zstdCmd, "-l", fileName)
	if err != nil {
		return 0, errors.Wrapf(err, "zst command failed %s -l %s", zstdCmd, fileName)
	}
	outLines := strings.Split(outStr, "\n")
	for i, line := range outLines {
		if i == 0 {
			if strings.Contains(line, "Uncompressed") {
				continue
			} else {
				return 0, errors.Errorf("can not get Uncompressed for %s", fileName)
			}
		}
		if i == 1 {
			cols := strings.Fields(line)
			readableBytes := strings.ReplaceAll(strings.ReplaceAll(cols[4]+cols[5], "i", ""), " ", "")
			bytesNum, err := cmutil.ParseSizeInBytesE(readableBytes)
			if err != nil {
				return 0, errors.Wrapf(err, "fail to parse size %s for %s", readableBytes, fileName)
			}
			return bytesNum, nil
		}
	}
	return 0, errors.Errorf("unknown error, zst -l %s output error", fileName)
}

func tarBallWithEncrypt(tarFilename string, srcFilename string) error {
	encryptCmd := []string{"openssl", "enc", "-aes-256-cbc", "-salt", "-k", "aaaa", "-out", "aaaa.tar.enc"}
	//encryptCmd := []string{"xbcrypt", "--encrypt=AES256"}
	tarCmd := []string{"tar", "-rf", "-", "dir1"}
	cmdStr := fmt.Sprintf("%s| pv | %s ", strings.Join(tarCmd, " "), strings.Join(encryptCmd, " "))
	fmt.Println(cmdStr)
	return nil
}

// ParseTarFilename 从 tar file name 中解析出 targetName
// 因为 tar name 生成规则在此
func ParseTarFilename(fileName string) string {
	if !strings.Contains(fileName, ".tar") {
		return ""
	}
	filename := filepath.Base(fileName)
	reg := regexp.MustCompile(`(.*?)(_\d+)?\.tar.*`)
	if m := reg.FindStringSubmatch(filename); len(m) >= 2 {
		return m[1]
	}
	return ""
}
