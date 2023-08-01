package dbareport

import (
	"bufio"
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/google/uuid"
)

// GenerateUUid Generate UUid
func GenerateUUid() (string, error) {
	uuids, err := uuid.NewUUID()
	if err != nil {
		logger.Log.Error("failed to generate Uuid, err: ", err)
		return "", err
	}
	return uuids.String(), nil
}

// GetFileType get the type of backup file
func GetFileType(fileName string) (fileType string) {
	if strings.HasSuffix(fileName, ".tar") {
		fileType = "tar"
	} else if strings.HasSuffix(fileName, ".priv") {
		fileType = "priv"
	} else if strings.HasSuffix(fileName, ".index") {
		fileType = "index"
	} else {
		fileType = "other"
	}
	return fileType
}

type mydumperMetadata struct {
	DumpStarted  string
	DumpFinished string
	MasterStatus map[string]string
	SlaveStatus  map[string]string
	Tables       map[string]interface{}
}

func parseMydumperMetadata(metadataFile string) (*mydumperMetadata, error) {
	metafile, err := os.Open(metadataFile)
	if err != nil {
		return nil, err
	}
	defer metafile.Close()

	var metadata = &mydumperMetadata{
		MasterStatus: map[string]string{},
		SlaveStatus:  map[string]string{},
		Tables:       map[string]interface{}{},
	}
	var flagMaster, flagSlave, flagTable bool
	// lines := cmutil.SplitAnyRuneTrim(string(bs), "\n")
	var l string // one line
	buf := bufio.NewScanner(metafile)
	for buf.Scan() {
		l = buf.Text()
		logger.Log.Debugf("metadata line: %s", l)
		if strings.HasPrefix(l, "# Started dump at:") {
			metadata.DumpStarted = strings.Trim(strings.TrimPrefix(l, "# Started dump at:"), "' ")
			continue
		} else if strings.HasPrefix(l, "# Finished dump at:") {
			metadata.DumpFinished = strings.Trim(strings.TrimPrefix(l, "# Finished dump at:"), "' ")
			continue
		} else if strings.HasPrefix(l, "[master]") { // 当在 master 备份时，只有这个，当在 slave 上备份时，这代表的是 slave的位点
			flagMaster = true
			flagSlave = false
			flagTable = false
			continue
		} else if strings.HasPrefix(l, "[replication]") {
			flagSlave = true
			flagMaster = false
			flagTable = false
			continue
		} else if strings.HasPrefix(l, "[`") { // table info
			flagTable = true
			flagMaster = false
			flagSlave = false
			continue
		}
		if strings.Contains(l, "=") {
			// parse master / slave info
			// # Channel_Name = '' # It can be use to setup replication FOR CHANNEL
			kv := strings.SplitN(l, "=", 2)
			key := strings.TrimSpace(strings.TrimLeft(kv[0], "#"))
			valTmp := strings.SplitN(kv[1], "# ", 2)
			val := strings.TrimSpace(strings.Trim(valTmp[0], "'"))
			logger.Log.Debugf("key=%s val=%s", key, val)
			if flagMaster {
				metadata.MasterStatus[key] = val
			} else if flagSlave {
				metadata.SlaveStatus[key] = val
			} else if flagTable {
				// metadata.Tables[key] = val
				continue
			}
		} else {
			continue
		}
	}
	return metadata, nil
}

// openXtrabackupFile parse xtrabackup_info
func openXtrabackupFile(binpath string, fileName string, tmpFileName string) (*os.File, error) {
	if exist, _ := util.FileExist(fileName); exist {
		util.CopyFile(tmpFileName, fileName)
	} else if exist, _ := util.FileExist(fileName + ".qp"); exist {
		qpressStr := fmt.Sprintf(`%s -do %s > %s`, binpath, fileName+".qp", tmpFileName)
		if err := util.ExeCommand(qpressStr); err != nil {
			return nil, err
		}
	} else {
		err := fmt.Errorf("%s dosen't exist", fileName)
		return nil, err
	}
	tmpFile, err := os.Open(tmpFileName)
	if err != nil {
		return nil, err
	}
	return tmpFile, nil
}

// parseXtraInfo get xtrabackup start_time / end_time
func parseXtraInfo(backupResult *BackupResult, binpath string, fileName string, tmpFileName string) error {
	tmpFile, err := openXtrabackupFile(binpath, fileName, tmpFileName)
	if err != nil {
		return err
	}
	defer func() {
		_ = tmpFile.Close()
	}()

	buf := bufio.NewScanner(tmpFile)
	var startTime, endTime string
	for buf.Scan() {
		line := buf.Text()
		if strings.HasPrefix(line, "start_time = ") {
			startTime = strings.TrimPrefix(line, "start_time = ")
			backupResult.BackupBeginTime = startTime
		}
		if strings.HasPrefix(line, "end_time = ") {
			endTime = strings.TrimPrefix(line, "end_time = ")
			backupResult.BackupEndTime = endTime
		}
	}
	return nil
}

// parseXtraTimestamp get consistentTime from xtrabackup_timestamp_info(if exists)
func parseXtraTimestamp(backupResult *BackupResult, binpath string, fileName string, tmpFileName string) error {
	tmpFile, err := openXtrabackupFile(binpath, fileName, tmpFileName)
	xtrabackupTimestampFileExist := true
	if err != nil {
		xtrabackupTimestampFileExist = false
		//return nil
	}
	defer func() {
		_ = tmpFile.Close()
	}()
	if xtrabackupTimestampFileExist {
		buf := bufio.NewScanner(tmpFile)
		for buf.Scan() {
			line := buf.Text()
			consistentTime, err := time.Parse("20060102_150405", line)
			if err != nil {
				return err
			}
			backupResult.ConsistentBackupTime = consistentTime.Format("2006-01-02 15:04:05")
		}
	} else {
		// 此时刚备份完成，还没有开始打包，这里把当前时间认为是 consistent_time，不完善！
		logger.Log.Warnf("xtrabackup_info file not found: %s, use current time as Consistent Time", fileName)
		// TODO 时区问题，待处理
		backupResult.ConsistentBackupTime = time.Now().Format("2006-01-02 15:04:05")
	}
	return nil
}

// parseXtraBinlogInfo parse xtrabackup_binlog_info to get master info
func parseXtraBinlogInfo(backupResult *BackupResult, binpath string, fileName string, tmpFileName string) error {
	tmpFile, err := openXtrabackupFile(binpath, fileName, tmpFileName)
	if err != nil {
		return err
	}
	defer func() {
		_ = tmpFile.Close()
	}()
	showMasterStatus := &StatusInfo{
		MasterHost: backupResult.MysqlHost, // use backup_host as local binlog file_pos host
		MasterPort: backupResult.MysqlPort,
	}
	buf := bufio.NewScanner(tmpFile)
	for buf.Scan() {
		line := buf.Text()
		re := regexp.MustCompile(`\S+`)
		words := re.FindAllString(line, -1)
		showMasterStatus.BinlogFile = words[0]
		showMasterStatus.BinlogPos = words[1]
		if len(words) >= 3 {
			showMasterStatus.Gtid = words[2]
		}
	}
	backupResult.BinlogInfo.ShowMasterStatus = showMasterStatus
	return nil
}

// parseXtraSlaveInfo parse xtrabackup_slave_info to get slave info
func parseXtraSlaveInfo(backupResult *BackupResult, binpath string, fileName string, tmpFileName string) error {
	tmpFile, err := openXtrabackupFile(binpath, fileName, tmpFileName)
	if err != nil {
		return err
	}
	defer func() {
		_ = tmpFile.Close()
	}()
	showSlaveStatus := &StatusInfo{
		MasterHost: backupResult.MasterHost,
		MasterPort: backupResult.MysqlPort,
	}
	buf := bufio.NewScanner(tmpFile)
	for buf.Scan() {
		line := buf.Text()
		re := regexp.MustCompile(`MASTER_LOG_FILE='(\S+)',\s+MASTER_LOG_POS=(\d+);`)
		matches := re.FindStringSubmatch(line)
		if len(matches) == 3 {
			showSlaveStatus.BinlogFile = matches[1]
			showSlaveStatus.BinlogPos = matches[2]
		}
	}
	backupResult.BinlogInfo.ShowSlaveStatus = showSlaveStatus
	return nil
}
