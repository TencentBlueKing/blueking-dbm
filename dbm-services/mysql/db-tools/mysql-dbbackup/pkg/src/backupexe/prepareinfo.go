package backupexe

import (
	"bufio"
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

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
			val := strings.TrimSpace(strings.Trim(valTmp[0], "' "))
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
// return startTime,endTime,error
func parseXtraInfo(qpress string, fileName string, tmpFileName string, metaInfo *dbareport.IndexContent) error {
	tmpFile, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	defer func() {
		_ = tmpFile.Close()
	}()
	if err != nil {
		return err
	}

	buf := bufio.NewScanner(tmpFile)
	var startTimeStr, endTimeStr string
	for buf.Scan() {
		line := buf.Text()
		if strings.HasPrefix(line, "start_time = ") {
			startTimeStr = strings.TrimPrefix(line, "start_time = ")
			metaInfo.BackupBeginTime, err = time.ParseInLocation(cst.XtrabackupTimeLayout, startTimeStr, time.Local)
			if err != nil {
				return errors.Wrapf(err, "parse BackupBeginTime %s", startTimeStr)
			}
		}
		if strings.HasPrefix(line, "end_time = ") {
			endTimeStr = strings.TrimPrefix(line, "end_time = ")
			metaInfo.BackupEndTime, err = time.ParseInLocation(cst.XtrabackupTimeLayout, endTimeStr, time.Local)
			if err != nil {
				return errors.Wrapf(err, "parse BackupEndTime %s", endTimeStr)
			}
		}
	}
	return nil
}

// parseXtraTimestamp get consistentTime from xtrabackup_timestamp_info(if exists)
func parseXtraTimestamp(qpress string, fileName string, tmpFileName string, metaInfo *dbareport.IndexContent) error {
	tmpFile, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	defer func() {
		_ = tmpFile.Close()
	}()
	if err != nil {
		return err
	} else {
		buf := bufio.NewScanner(tmpFile)
		for buf.Scan() {
			line := buf.Text()
			metaInfo.BackupConsistentTime, err = time.ParseInLocation("20060102_150405", line, time.Local)
			if err != nil {
				return errors.Wrapf(err, "parse BackupConsistentTime %s", line)
			}
		}
	}
	return nil
}

// parseXtraBinlogInfo parse xtrabackup_binlog_info to get master info
func parseXtraBinlogInfo(qpress string, fileName string, tmpFileName string) (*dbareport.StatusInfo, error) {
	tmpFile, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = tmpFile.Close()
	}()
	showMasterStatus := &dbareport.StatusInfo{
		//MasterHost: backupResult.MysqlHost, // use backup_host as local binlog file_pos host
		//MasterPort: backupResult.MysqlPort,
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
	return showMasterStatus, nil
}

// parseXtraSlaveInfo parse xtrabackup_slave_info to get slave info
func parseXtraSlaveInfo(qpress string, fileName string, tmpFileName string) (*dbareport.StatusInfo, error) {
	tmpFile, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	if err != nil {
		return nil, err
	}
	defer func() {
		_ = tmpFile.Close()
	}()
	showSlaveStatus := &dbareport.StatusInfo{
		//MasterHost: backupResult.MasterHost,
		//MasterPort: backupResult.MysqlPort,
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
	return showSlaveStatus, nil
}
