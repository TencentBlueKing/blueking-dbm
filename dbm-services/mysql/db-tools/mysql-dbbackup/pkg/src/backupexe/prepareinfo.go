package backupexe

import (
	"bufio"
	"bytes"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
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

// parseMysqldumpMetadata 从 mysqldump sql 文件里解析 change master / change slave 命令
// 命令被注释，在文件开头的前几行
func parseMysqldumpMetadata(sqlFilePath string, serverVersion string) (*mydumperMetadata, error) {
	logger.Log.Infof("start parseMysqldumpMetadata from %s", sqlFilePath)
	sqlFile, err := os.Open(sqlFilePath)
	if err != nil {
		return nil, err
	}
	defer sqlFile.Close()
	var metadata = &mydumperMetadata{
		MasterStatus: map[string]string{},
		SlaveStatus:  map[string]string{},
		Tables:       map[string]interface{}{},
	}

	var bufScanner *bufio.Scanner
	if strings.HasSuffix(sqlFilePath, cst.ZstdSuffix) {
		cmds := []string{"head", "-c", "4096", sqlFilePath, "|", CmdZstd, "-d", "-c"}
		outBuf, _, err := cmutil.ExecCommandReturnBytes(true, "", cmds[0], cmds[1:]...)

		if len(outBuf) < 100 { // 返回小于这个长度，肯定非法了，重试一遍
			// https://github.com/facebook/zstd/issues/1358 The maximum block size is indeed a hard limit of 128 KB
			zstdMaxBlockSize := cast.ToString(128 * 1024 * 2)
			cmds = []string{"head", "-c", zstdMaxBlockSize, sqlFilePath, "|", CmdZstd, "-d", "-c"}
			outBuf, _, err = cmutil.ExecCommandReturnBytes(true, "", cmds[0], cmds[1:]...)
		}
		if err != nil {
			logger.Log.Warnf("zstd decode first 4096 bytes failed from %s, err:%s", sqlFilePath, err.Error())
		}
		if len(outBuf) < 100 { // 返回小于这个长度，非法报错
			return nil, errors.Errorf("failed to get binlog position from zst file %s", sqlFilePath)
		}
		bufScanner = bufio.NewScanner(bytes.NewBuffer(outBuf))
	} else {
		bufScanner = bufio.NewScanner(sqlFile)
	}

	var l string                                                                   // one line
	reMaster := `CHANGE MASTER TO MASTER_LOG_FILE='([^']+)', MASTER_LOG_POS=(\d+)` // 本机的位点
	if cmutil.MySQLVersionCompare(serverVersion, "8.4") >= 0 {
		reMaster = `CHANGE REPLICATION SOURCE TO SOURCE_LOG_FILE='([^']+)', SOURCE_LOG_POS=(\d+)`
	}
	//reSlave := `CHANGE SLAVE TO MASTER_LOG_FILE='([^']+)', MASTER_LOG_POS=(\d+)`   // 本机的 远端master 的位点
	reShowMaster := regexp.MustCompile(reMaster)
	//reShowSlave := regexp.MustCompile(reSlave)
	for bufScanner.Scan() {
		l = bufScanner.Text()
		matches := reShowMaster.FindStringSubmatch(l)
		if len(matches) == 3 {
			metadata.MasterStatus["File"] = matches[1]
			metadata.MasterStatus["Position"] = matches[2]
			break
		}
	}
	return metadata, nil
}

func parseMydumperMetadata(metadataFile string) (*mydumperMetadata, error) {
	logger.Log.Infof("start parseMydumperMetadata %s", metadataFile)
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
		} else if strings.HasPrefix(l, "[master]") || strings.HasPrefix(l, "[source]") {
			// 当在 master 备份时，只有这个，当在 slave 上备份时，这代表的是 slave的位点
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
			key := strings.ToLower(strings.TrimSpace(strings.TrimLeft(kv[0], "#")))
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

// mydumperMetadataV2 解析 mydumper 新版 metadata 的结构体
type mydumperMetadataV2 struct {
	DumpStarted  string
	DumpFinished string
	// [source] section: 本机的 binlog 位点（包括注释行和非注释行的 kv）
	MasterStatus map[string]string
	// [replication] section: 远端 master 的 binlog 位点及 show slave status 详情
	SlaveStatus map[string]string
	// [config] section 的配置项（可能出现多次，后面的会覆盖前面的）
	Config map[string]string
	// [myloader_session_variables] section
	SessionVariables map[string]string
	// [`db`.`table`] section 不保存，内容过多会造成不必要的开销
}

// parseMydumperMetadataV2 解析 mydumper 新版 metadata 文件
// 支持 section: [config], [myloader_session_variables], [source], [replication], [`db`.`table`]
func parseMydumperMetadataV2(metadataFile string) (*mydumperMetadataV2, error) {
	logger.Log.Infof("start parseMydumperMetadataV2 %s", metadataFile)
	metafile, err := os.Open(metadataFile)
	if err != nil {
		return nil, errors.Wrapf(err, "open metadata file %s", metadataFile)
	}
	defer metafile.Close()

	metadata := &mydumperMetadataV2{
		MasterStatus:     make(map[string]string),
		SlaveStatus:      make(map[string]string),
		Config:           make(map[string]string),
		SessionVariables: make(map[string]string),
	}

	type sectionType int
	const (
		sectionNone sectionType = iota
		sectionConfig
		sectionSession
		sectionSource
		sectionReplication
		sectionMaster
		sectionTable
	)

	var curSection sectionType

	buf := bufio.NewScanner(metafile)
	for buf.Scan() {
		line := buf.Text()
		trimmed := strings.TrimSpace(line)

		// 空行跳过
		if trimmed == "" {
			continue
		}

		// 解析 Started/Finished dump 时间（文件首尾的特殊注释）
		if strings.HasPrefix(trimmed, "# Started dump at:") {
			metadata.DumpStarted = strings.TrimSpace(strings.TrimPrefix(trimmed, "# Started dump at:"))
			continue
		}
		if strings.HasPrefix(trimmed, "# Finished dump at:") {
			metadata.DumpFinished = strings.TrimSpace(strings.TrimPrefix(trimmed, "# Finished dump at:"))
			continue
		}

		// 检测 section header: [xxx]
		if strings.HasPrefix(trimmed, "[") && strings.HasSuffix(trimmed, "]") {
			sectionName := trimmed[1 : len(trimmed)-1]
			switch {
			case sectionName == "config":
				curSection = sectionConfig
			case sectionName == "myloader_session_variables":
				curSection = sectionSession
			case sectionName == "source":
				curSection = sectionSource
			case sectionName == "master":
				curSection = sectionMaster
			case sectionName == "replication":
				curSection = sectionReplication
			case strings.HasPrefix(sectionName, "`"):
				curSection = sectionTable
			default:
				curSection = sectionNone
			}
			continue
		}

		// 判断是否为注释行（以 # 开头）
		isComment := strings.HasPrefix(trimmed, "#")

		// 纯注释行如果不含 = 则跳过（如 "# Channel_Name = '' # It can be ..." 需要解析）
		if isComment && !strings.Contains(trimmed, "=") {
			continue
		}

		// 非 kv 行跳过
		if !strings.Contains(trimmed, "=") {
			continue
		}

		// 解析 key = value
		raw := trimmed
		if isComment {
			// 去掉前导的 '#' 字符
			raw = strings.TrimSpace(strings.TrimLeft(trimmed, "#"))
		}

		eqIdx := strings.Index(raw, "=")
		if eqIdx < 0 {
			continue
		}
		key := strings.ToLower(strings.TrimSpace(raw[:eqIdx]))
		valRaw := raw[eqIdx+1:]

		// 去掉行内尾部注释（" # " 后面的内容）
		if commentIdx := strings.Index(valRaw, " # "); commentIdx >= 0 {
			valRaw = valRaw[:commentIdx]
		}
		// 去掉首尾空格，再去掉外层引号
		val := strings.TrimSpace(valRaw)
		val = trimQuotes(val)

		if key == "" {
			continue
		}

		// 根据当前 section 分发
		switch curSection {
		case sectionSource:
			metadata.MasterStatus[key] = val
		case sectionReplication:
			metadata.SlaveStatus[key] = val
			// map to old style
			switch key {
			case "source_log_file":
				metadata.SlaveStatus["relay_master_log_file"] = val
			case "source_log_pos":
				metadata.SlaveStatus["exec_master_log_pos"] = val
			case "source_auto_position":
				metadata.SlaveStatus["auto_position"] = val
			case "source_host":
				metadata.SlaveStatus["master_host"] = val
			case "source_port":
				metadata.SlaveStatus["master_port"] = val
			}
			// map to new style
			switch key {
			case "relay_master_log_file":
				metadata.SlaveStatus["source_log_file"] = val
			case "exec_master_log_pos":
				metadata.SlaveStatus["source_log_pos"] = val
			case "auto_position":
				metadata.SlaveStatus["source_auto_position"] = val
			case "master_host":
				metadata.SlaveStatus["source_host"] = val
			case "master_port":
				metadata.SlaveStatus["source_port"] = val
			}
		case sectionMaster:
			metadata.MasterStatus[key] = val
			// map to old style
			switch key {
			case "source_log_file":
				metadata.MasterStatus["file"] = val
			case "source_log_pos":
				metadata.MasterStatus["position"] = val
			}
			// map to new style
			switch key {
			case "file":
				metadata.MasterStatus["source_log_file"] = val
			case "position":
				metadata.MasterStatus["source_log_pos"] = val
			}
		case sectionConfig:
			metadata.Config[key] = val
		case sectionSession:
			metadata.SessionVariables[key] = val
		case sectionTable:
			continue
		default:
			continue
		}
	}

	if err := buf.Err(); err != nil {
		return nil, errors.Wrap(err, "scan metadata file")
	}

	logger.Log.Infof("parseMydumperMetadataV2 done: masterStatus=%v, slaveStatus=%v",
		metadata.MasterStatus, metadata.SlaveStatus)
	return metadata, nil
}

// trimQuotes 去掉字符串外层的单引号或双引号
func trimQuotes(s string) string {
	if len(s) >= 2 {
		if (s[0] == '\'' && s[len(s)-1] == '\'') || (s[0] == '"' && s[len(s)-1] == '"') {
			return s[1 : len(s)-1]
		}
	}
	return s
}

// openXtrabackupFile parse xtrabackup_info
// 因为文件不大，直接 readall
func openXtrabackupFile(binpath string, fileName string, tmpFileName string) (*bytes.Buffer, error) {
	readCmd := []string{}
	if exist, _ := util.FileExist(fileName); exist {
		readCmd = append(readCmd, "cat", fileName)
	} else if exist, _ = util.FileExist(fileName + cst.QpSuffix); exist {
		readCmd = append(readCmd, binpath, "-do", fileName+cst.QpSuffix)
	} else if exist, _ = util.FileExist(fileName + cst.ZstdSuffix); exist {
		readCmd = append(readCmd, CmdZstd, "-dc", fileName+cst.ZstdSuffix)
	} else {
		err := fmt.Errorf("%s does not exist", fileName)
		return nil, err
	}
	content, errBytes, err := cmutil.ExecCommandReturnBytes(false, "", readCmd[0], readCmd[1:]...)
	if err != nil {
		return nil, errors.WithMessagef(err, "openXtrabackupFile %s got err:%s", fileName, string(errBytes))
	}
	return bytes.NewBuffer(content), nil
}

func zstdcat(fileName string) (*bytes.Buffer, error) {
	content, errBytes, err := cmutil.ExecCommandReturnBytes(false, "", CmdZstd, "-dc", fileName)
	if err != nil {
		return nil, errors.WithMessagef(err, "zstdcat %s got err:%s", fileName, string(errBytes))
	}
	return bytes.NewBuffer(content), nil
}

// parseXtraInfo get start_time / end_time / binlog pos from xtrabackup_info
// return startTime,endTime,error
/*
uuid = xx-4347-11ef-8de0-xxxxxxxxx
name =
tool_name = xtrabackup_57
tool_command = --defaults-file=/etc/my.cnf.3306 --host=x.x.x.x --port=3306 --user=xx --password=...
tool_version = 2.4.11
ibbackup_version = 2.4.11
server_version = 5.7.20-tmysql-3.3-log
start_time = 2024-07-16 15:44:13
end_time = 2024-07-16 15:44:20
lock_time = 0
binlog_pos = filename 'binlog20000.000353', position '181942'
binlog_pos = filename 'binlog20000.000014', position '238', GTID of the last change '1234-122-11f1-a8f9-525400cfbfb9:3-237,1234-122-11f1-bb8d-525400ccfd94:1-22'
innodb_from_lsn = 0
innodb_to_lsn = 980247078
partial = N
incremental = N
format = file
compact = N
compressed = compressed
encrypted = N
lock_ddl_type = OFF
backup_size = 1785885
uncompressed_backup_size = 1137583816
*/
func parseXtraInfo(qpress string, fileName string, tmpFileName string, metaInfo *dbareport.IndexContent) error {
	fileBytes, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	if err != nil {
		return err
	}
	scanner := bufio.NewScanner(fileBytes)
	var startTimeStr, endTimeStr string
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "start_time = ") { // start_time = 2024-07-16 15:44:13
			startTimeStr = strings.TrimPrefix(line, "start_time = ")
			metaInfo.BackupBeginTime, err = time.ParseInLocation(cst.XtrabackupTimeLayout, startTimeStr, time.Local)
			if err != nil {
				return errors.Wrapf(err, "parse BackupBeginTime %s", startTimeStr)
			}
		}
		if strings.HasPrefix(line, "end_time = ") { // end_time = 2024-07-16 15:44:20
			endTimeStr = strings.TrimPrefix(line, "end_time = ")
			metaInfo.BackupEndTime, err = time.ParseInLocation(cst.XtrabackupTimeLayout, endTimeStr, time.Local)
			if err != nil {
				return errors.Wrapf(err, "parse BackupEndTime %s", endTimeStr)
			}
		}
		// binlog_pos = filename 'binlog20000.000353', position '181942'
		// binlog_pos = filename 'binlog20000.000014', position '238', GTID of the last change 'xx'
		if strings.HasPrefix(line, "binlog_pos =") {
			regBinlogPos := regexp.MustCompile(`.* filename '(.+\.\d+)', position '(\d+)'`)
			if matches := regBinlogPos.FindStringSubmatch(line); len(matches) == 3 {
				metaInfo.BinlogInfo.ShowMasterStatus = &dbareport.StatusInfo{
					BinlogFile: matches[1],
					BinlogPos:  matches[2],
				}
			}
		}

		// parse uncompressed_backup_size
		if strings.HasPrefix(line, "uncompressed_backup_size") {
			regUncompressSize := regexp.MustCompile(`uncompressed_backup_size\s*=\s*(\d+)`)
			if matches := regUncompressSize.FindStringSubmatch(line); len(matches) == 2 {
				metaInfo.ExtraFields.TotalSizeKBUncompress, _ = strconv.ParseInt(matches[1], 10, 64)
			}
		}
	}
	return nil
}

// parseXtraTimestamp get consistentTime from xtrabackup_timestamp_info(if exists)
/*
20240716_154420
*/
func parseXtraTimestamp(qpress string, fileName string, tmpFileName string, metaInfo *dbareport.IndexContent) error {
	fileBytes, err := openXtrabackupFile(qpress, fileName, tmpFileName)

	if err != nil {
		return err
	} else {
		scanner := bufio.NewScanner(fileBytes)
		for scanner.Scan() {
			line := scanner.Text()
			metaInfo.BackupConsistentTime, err = time.ParseInLocation("20060102_150405", line, time.Local)
			if err != nil {
				return errors.Wrapf(err, "parse BackupConsistentTime %s", line)
			}
		}
	}
	return nil
}

// parseXtraBinlogInfo parse xtrabackup_binlog_info / xtrabackup_binlog_pos_innodb to get master info
/*
binlog20000.000353      181942
*/
func parseXtraBinlogInfo(qpress string, fileName string, tmpFileName string) (*dbareport.StatusInfo, error) {
	fileBytes, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	if err != nil {
		return nil, err
	}
	showMasterStatus := &dbareport.StatusInfo{
		//MasterHost: backupResult.MysqlHost, // use backup_host as local binlog file_pos host
		//MasterPort: backupResult.MysqlPort,
	}
	// 预期应该只有一条记录
	fileContentStr := strings.ReplaceAll(fileBytes.String(), ",\n", ",")
	words := strings.Fields(fileContentStr)
	if len(words) < 2 {
		return nil, errors.Errorf("failed to parse xtrabackup_binlog_info, get %s", fileContentStr)
	}
	showMasterStatus.BinlogFile = words[0]
	showMasterStatus.BinlogPos = words[1]
	if len(words) >= 3 {
		showMasterStatus.Gtid = words[2]
	}
	return showMasterStatus, nil
}

// parseXtraSlaveInfo parse xtrabackup_slave_info to get slave info
/*
CHANGE MASTER TO MASTER_LOG_FILE='binlog20000.009159', MASTER_LOG_POS=6488;
CHANGE REPLICATION SOURCE TO SOURCE_LOG_FILE='binlog20000.000010', SOURCE_LOG_POS=1216;
*/
func parseXtraSlaveInfo(qpress string, fileName string, tmpFileName string) (*dbareport.StatusInfo, error) {
	fileBytes, err := openXtrabackupFile(qpress, fileName, tmpFileName)
	if err != nil {
		return nil, err
	}

	showSlaveStatus := &dbareport.StatusInfo{
		//MasterHost: backupResult.MasterHost,
		//MasterPort: backupResult.MysqlPort,
	}
	re := regexp.MustCompile(`MASTER_LOG_FILE='(\S+)',\s+MASTER_LOG_POS=(\d+)`)
	if strings.Contains(fileBytes.String(), "SOURCE_LOG_FILE") {
		re = regexp.MustCompile(`SOURCE_LOG_FILE='(\S+)',\s+SOURCE_LOG_POS=(\d+)`)
	}
	scanner := bufio.NewScanner(fileBytes)
	for scanner.Scan() {
		line := scanner.Text()
		matches := re.FindStringSubmatch(line)
		if len(matches) == 3 {
			showSlaveStatus.BinlogFile = matches[1]
			showSlaveStatus.BinlogPos = matches[2]
		}
	}
	logger.Log.Warnf("parseXtraSlaveInfo=%+v", showSlaveStatus)
	return showSlaveStatus, nil
}
