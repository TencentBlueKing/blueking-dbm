package pitr

import (
	"bufio"
	"bytes"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mycmd"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"fmt"
	"io"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
)

var BinDir string

func getToolPath(name string) string {
	return path.Join(BinDir, "bin", name)
}

// Output 如果有别的程序调用mongo-recover，可以根据type == OUTPUT/SUCC/FAIL 过滤到有用的日志
func Output(format string, a ...interface{}) {
	//format = "OUTPUT "+ strings.TrimSuffix(format, "\n") + "\n"
	//return fmt.Printf(format, a...)
	log.WithField("type", "OUTPUT").Printf(format, a...)
}

// ExitSuccess print succ and exit
func ExitSuccess(format string, a ...interface{}) {
	log.WithField("type", "SUCC").Printf(format, a...)
}

// ExitFailed print error and exit
func ExitFailed(format string, a ...interface{}) {
	log.WithField("type", "FAIL").Printf(format, a...)
	os.Exit(1)

}

func saveLog(commandLine, restoreLogfile string, stdout, stderr string, err error) {
	buf1 := bytes.NewBufferString(stdout)
	buf2 := bytes.NewBufferString(stderr)
	SaveRestoreLog(commandLine, restoreLogfile, *buf1, *buf2, err)
}

// SaveRestoreLog 保存恢复日志
func SaveRestoreLog(commandLine, restoreLogfile string, outBuf, errBuf bytes.Buffer, err error) {
	if f, err2 := os.Create(restoreLogfile); err2 == nil {
		defer f.Close()
		f.WriteString("cmd: " + commandLine + "\n")
		f.WriteString("stdout begin:\n")
		f.Write(outBuf.Bytes())
		f.WriteString("\nstdout end\n")

		f.WriteString("stderr begin\n")
		f.Write(errBuf.Bytes())
		f.WriteString("\nstderr end\n")

		f.WriteString("golang error begin\n")
		f.WriteString(fmt.Sprintf("%v\n", err))
		f.WriteString("golang error end\n")
		log.Printf("Write restoreLogfile: %s succ", restoreLogfile)
	} else {
		log.Warnf("Write restoreLogfile: %s error", restoreLogfile)
	}
}

// ProcessLog 进度日志
type ProcessLog struct {
	t     time.Time
	Msg   string
	IsErr bool
}

// NewProcessLog 创建进度日志
func NewProcessLog(msg string, isErr bool) *ProcessLog {
	return &ProcessLog{
		t:     time.Now(),
		Msg:   msg,
		IsErr: isErr,
	}
}

// SendProcessLog 发送进度日志
func SendProcessLog(logChan chan *ProcessLog, msg string) {
	if logChan == nil {
		return
	}
	logChan <- NewProcessLog(msg, false)
}

// SendErrorProcessLog 发送进度日志
func SendErrorProcessLog(logChan chan *ProcessLog, msg string) {
	if logChan == nil {
		return
	}
	logChan <- NewProcessLog(msg, true)
}

// UntarFull 解压全量备份
func UntarFull(backupFileDir string, file *BackupFileName) (fullTmpDir, subDirName string, gzip bool, err error) {
	if err = os.Chdir(backupFileDir); err != nil {
		err = errors.Wrap(err, "Cannot chdir to %s")
	}

	subDirName = strings.TrimSuffix(file.FileName, ".gz")
	subDirName = strings.TrimSuffix(subDirName, ".tar")
	fullTmpDir = path.Join("tmp", subDirName, "full")

	if _, err = os.Stat(fullTmpDir); err == nil {
		err = fmt.Errorf("tmpDir:[%s] already exists, please delete it first", fullTmpDir)
		return
	}
	if err = os.MkdirAll(fullTmpDir, os.FileMode(0755)); err != nil {
		err = fmt.Errorf("mkdir %s err:%v", fullTmpDir, err)
		return
	}

	var tarArg string
	tarCmd := mycmd.NewCmdBuilder().Append("tar")
	if strings.HasSuffix(file.FileName, ".gz") {
		gzip = false
		tarArg = "zxf"
	} else {
		gzip = true
		tarArg = "xf"
	}
	tarCmd.Append(tarArg, file.FileName, "-C", fullTmpDir)

	var ebuf string
	_, _, ebuf, err = tarCmd.RunByBash("", time.Hour*24)
	if err != nil {
		err = fmt.Errorf("%s return error %s, stdout:%s", tarCmd.GetCmdLine("", false), err, ebuf)
	}
	return
}

// DoMongoRestoreFULL 导入全量备份
func DoMongoRestoreFULL(bin string, conn *mymongo.MongoHost, file *BackupFileName, backupFileDir string, logChan chan *ProcessLog) (string, error) {
	// fmt.Printf("DoMongoRestore: %s %s to %s:%s\n", file.Type, file.FileName, conn.Host, conn.Port)
	SendProcessLog(logChan, fmt.Sprintf("start to untar %s ", file.FileName))
	fullTmpDir, subDirName, gzip, err := UntarFull(backupFileDir, file)
	if err != nil {
		SendErrorProcessLog(logChan, fmt.Sprintf("UntarFull return %s", err.Error()))
		return "", errors.Wrap(err, "UntarFull")
	}
	SendProcessLog(logChan, fmt.Sprintf("untar %s end. dir:%s", file.FileName, path.Join(fullTmpDir, subDirName)))
	adminDbDir := filepath.Join(fullTmpDir, subDirName, "dump", "admin")
	adminFileList, err := os.ReadDir(adminDbDir)
	if err != nil {
		return "", fmt.Errorf("no admin database:%s %v", adminDbDir, err)
	}
	var deletedFileNames []string
	for _, fi := range adminFileList {
		if !fi.IsDir() && strings.HasPrefix(fi.Name(), "system.") {
			fullName := filepath.Join(adminDbDir, fi.Name())
			if err2 := os.Remove(fullName); err2 != nil {
				return "", fmt.Errorf("rm %q faild: %w", fullName, err2)
			}
			deletedFileNames = append(deletedFileNames, fi.Name())
		}
	}
	SendProcessLog(logChan, fmt.Sprintf("rm system files at dump/admin/ %s", deletedFileNames))
	SendProcessLog(logChan, fmt.Sprintf("start to mongorestore %s", file.FileName))
	dumpDir := path.Join(fullTmpDir, subDirName, "dump")
	restoreLogfile := path.Join(fullTmpDir, subDirName, "restore.log")

	restoreCmd := mycmd.NewCmdBuilder().Append(bin).Append("--host",
		conn.Host, "--port", conn.Port, "--authenticationDatabase", conn.AuthDb, "--oplogReplay")
	if len(conn.User) > 0 {
		restoreCmd.Append("-u", conn.User)
	}
	if len(conn.Pass) > 0 {
		restoreCmd.Append("-p").AppendPassword(conn.Pass)
	}
	if gzip {
		restoreCmd.Append("--gzip")
	}
	restoreCmd.Append("--dir", dumpDir)
	errReader, errWriter := io.Pipe()
	var outBuf, errBuf bytes.Buffer
	bgCmd := mycmd.NewExecCmdBg()
	bgCmd.SetOutput(io.Writer(&outBuf), errWriter)
	bin, args := restoreCmd.GetCmd()
	bgCmd.Run(86400*7, bin, args)
	wg := &sync.WaitGroup{}
	wg.Add(1)
	// 后台读取errReader，
	go func() {
		defer wg.Done()
		scanner := bufio.NewScanner(errReader)
		// optionally, resize scanner's capacity for lines over 64K, see next example
		for scanner.Scan() {
			newLine := scanner.Text()
			errBuf.WriteString(newLine)
			errBuf.Write([]byte("\n"))
			SendProcessLog(logChan, newLine)
		}
		if err = scanner.Err(); err != nil {
			SendProcessLog(logChan, fmt.Sprintf("scanner.Err() %s", scanner.Err()))
		}
	}()
	bgCmd.Wait()      // 等待命令完成
	errWriter.Close() // 关闭管道，让scanner退出
	wg.Wait()         // 等待scanner退出

	exitCode := 0
	stdout := outBuf.String()

	saveLog(restoreCmd.GetCmdLine("", true), restoreLogfile, stdout, errBuf.String(), err)
	// todo 检查日志中是否有一些异常字串 比如Duplicate keys
	// todo 隐患 当出现大量Duplicate日志时，obuf/ebuf需要相应的内存存储引起oom，要改为直接写入文件
	if err != nil {
		SendErrorProcessLog(logChan,
			fmt.Sprintf("return code %d error %s, stdout:%s stderr:%s", exitCode, err, stdout, cutString(errBuf.String(), 1024)))
		return "", fmt.Errorf("mongorestore return error %v", err)
	}
	return dumpDir, nil
}

func cutString(s string, maxLen int) string {
	if len(s) > maxLen+20 {
		cuttedLen := len(s) - maxLen
		return fmt.Sprintf("(%d bytes before)... ", cuttedLen) + s[:maxLen]
	}
	return s
}

// DoReplayOplog oplog dir/oplog.bson
func DoReplayOplog(bin string, conn *mymongo.MongoHost, backupFilePath string, recoverTime uint32, gzip bool) error {
	fmt.Printf("DoReplayOplog: %s to %s:%s\n", backupFilePath, conn.Host, conn.Port)

	if filepath.Base(backupFilePath) != "oplog.bson" {
		return fmt.Errorf("bad oplog name:%s", filepath.Base(backupFilePath))
	}

	oplogDir := filepath.Dir(backupFilePath)

	args := []string{"--host", conn.Host, "--port", conn.Port, "--authenticationDatabase", conn.AuthDb}
	if len(conn.User) > 0 {
		args = append(args, "-u", conn.User)
	}
	if len(conn.Pass) > 0 {
		args = append(args, "-p", conn.Pass)
	}

	//mongodump --oplog --gzip 产生的oplog.bson文件，虽然文件名为oplog.bson，但实际是gz压缩文件
	if gzip {
		args = append(args, "--gzip")
	}
	args = append(args, "--oplogReplay")

	//--oplogLimit $recovery_time_epoch:0
	if recoverTime > 0 {
		args = append(args, "--oplogLimit", fmt.Sprintf("%d:999", recoverTime))
	}

	//最后一个参数必须是
	args = append(args, "--dir", oplogDir)

	obuf, ebuf, err := DoCommand(bin, args...)
	commandLine := fmt.Sprintf("%s %s", bin, strings.Join(args, " "))
	logFile := path.Join(path.Dir(path.Dir(backupFilePath)), "restore.log")
	SaveRestoreLog(commandLine, logFile, obuf, ebuf, err)
	log.Printf("Exec commandLine: %s err:%v", commandLine, err)
	log.Printf("SaveRestoreLog: %s", logFile)
	return err
}

// FileExists https://stackoverflow.com/questions/12518876/how-to-check-if-a-file-exists-in-go
func FileExists(filePath string) (bool, error) {
	if _, err := os.Stat(filePath); err == nil {
		// path/to/whatever exists
		return true, nil

	} else if os.IsNotExist(err) {
		// path/to/whatever does *not* exist
		return false, nil
	} else {
		return false, err
		// Schrodinger: file may or may not exist. See err for details.

		// Therefore, do *NOT* use !os.IsNotExist(err) to test for file existence
	}
}

/*
DoMongoRestoreINCR 导入INCR.
*/
func DoMongoRestoreINCR(bin string, conn *mymongo.MongoHost, full *BackupFileName, incrList []*BackupFileName,
	recoverTime uint32, backupFileDir string, idx int) error {
	file := incrList[idx]
	// fmt.Printf("DoMongoRestoreINCR: %s [%d] %s to %s:%s\n", file.Type, idx, file.FileName, conn.Host, conn.Port)

	subDirName := full.FileName
	subDirName = strings.TrimSuffix(subDirName, ".gz")
	subDirName = strings.TrimSuffix(subDirName, ".tar")
	incrTmpDir := path.Join("tmp", subDirName, fmt.Sprintf("incr-%d", idx), "oplog")

	if err := os.Chdir(backupFileDir); err != nil {
		return fmt.Errorf("Cannot chdir to %s", backupFileDir)
	}
	if stat, err := os.Stat(incrTmpDir); err != nil {
		if err := os.MkdirAll(incrTmpDir, os.FileMode(0755)); err != nil {
			return fmt.Errorf("Cannot make dir %s", incrTmpDir)
		} else {
			log.Printf("[%s] mkdir [%s] succ", backupFileDir, incrTmpDir)
		}
	} else if !stat.IsDir() {
		return fmt.Errorf("Cannot make dir %s, because a same-name-file exists", incrTmpDir)
	}

	gzip := false
	oplogNewName := "oplog.bson"
	// oplog Relay
	if strings.HasSuffix(file.FileName, ".gz") {
		gzip = true
		DoCommand("cp", file.FileName, path.Join(incrTmpDir, oplogNewName))
	} else {
		gzip = false
		DoCommand("cp", file.FileName, path.Join(incrTmpDir, oplogNewName))
	}

	//DoCommand("gzip", "-d", path.Join(incrTmpDir,oplog_newname +".gz"))
	// V1版本:
	// 全量备份和增量备份是分别2个线程，全量只管做全量备份，增量备份只需要和它上一个增量备份衔接。
	// 这导致全量备份导入后，下一个增量备份文件里有和全量备份oplog重叠的部分
	if idx == 0 && file.Version == BackupFileVersionV1 {
		minTs := fmt.Sprintf("%d", full.LastTs.Sec)
		// Output("This is the First oplog after FULL")
		// Output("Delete First oplog.bson where time < %s (full time)", minTs)
		///bsonfilter --bsonFile ./path/to/oplog.bson  --outFile x.bson.new --min-ts 1576990774:1
		oldPath := path.Join(incrTmpDir, oplogNewName)
		newPath := path.Join(incrTmpDir, oplogNewName) + ".new"
		result, err := DoCommandV2("bsonfilter", "--bsonFile", oldPath, "--outFile", newPath, "--min-ts", minTs)
		logFile := path.Join(path.Dir(incrTmpDir), "bsonfilter.log")
		os.Rename(newPath, oldPath)
		SaveRestoreLog(result.Cmdline, logFile, result.Stdout, result.Stderr, err)
		//gzip is false after bsonfilter ...
		gzip = false
	}

	return DoReplayOplog(bin, conn, path.Join(incrTmpDir, oplogNewName), recoverTime, gzip)
}

func receiveLogBg() (*sync.WaitGroup, chan *ProcessLog) {
	logChan := make(chan *ProcessLog, 1)
	wg := &sync.WaitGroup{}
	wg.Add(1)
	go func() {
		defer wg.Done()
		for {
			select {
			case log, ok := <-logChan:
				if !ok {
					return
				}
				if log.IsErr {
					ExitFailed("%s", log.Msg)
				} else {
					Output("%s", log.Msg)
				}
			}
		}
	}()
	return wg, logChan
}

// DoRecover 从全量和增量文件中恢复到指定时间点.
func DoRecover(conn *mymongo.MongoHost, full *BackupFileName, incrList []*BackupFileName, recoverTime uint32, backupFileDir string) error {
	wd, _ := os.Getwd()
	log.Printf("WorkDir %s", wd)
	Output("WorkDir is %s", wd)

	// 处理日志
	wg, logChan := receiveLogBg()

	var err error
	// 导入日志时间可能比较长.
	_, err = DoMongoRestoreFULL("mongorestore", conn, full, backupFileDir, logChan)
	// ExitFailed("DoMongoRestoreFULL return %s", err.Error())

	if err != nil {
		SendErrorProcessLog(logChan, fmt.Sprintf("DoMongoRestoreFULL return %s", err.Error()))
		goto End
	}

	for idx, _ := range incrList {
		os.Chdir(wd)
		SendProcessLog(logChan, fmt.Sprintf("DoMongoRestoreINCR %s start", incrList[idx].FileName))
		if err = DoMongoRestoreINCR("mongorestore", conn, full, incrList, recoverTime, backupFileDir, idx); err != nil {
			// ExitFailed("DoMongoRestoreINCR %s return %s", incrList[idx].FileName, err.Error())
			SendErrorProcessLog(logChan, fmt.Sprintf("DoMongoRestoreINCR %s return %s", incrList[idx].FileName, err.Error()))
			goto End
		}
		SendProcessLog(logChan, fmt.Sprintf("DoMongoRestoreINCR %s end", incrList[idx].FileName))
	}

End:
	close(logChan)
	wg.Wait()
	if err == nil {
		ExitSuccess("done")
	}
	return err
}

// FindNeedFiles 找到需要的全量和增量文件
func FindNeedFiles(fileObjList []*BackupFileName, recoverTime uint32) (*BackupFileName, []*BackupFileName, error) {
	var fullList []*BackupFileName
	for _, file := range fileObjList {
		if file.Type != BackupTypeFull {
			continue
		}

		if file.LastTs.Sec <= recoverTime {
			fullList = append(fullList, file)
		}
	}

	if len(fullList) == 0 {
		return nil, nil, fmt.Errorf("no-full-file-found")
	}

	sort.Slice(fullList, func(i, j int) bool {
		return fullList[i].LastTs.Sec > fullList[j].LastTs.Sec
	})

	for _, file := range fullList {
		if incrList, err := FindIncrList(file, recoverTime, fileObjList); err == nil {
			return file, incrList, nil
		}
	}

	return nil, nil, fmt.Errorf("no-incr-file-found")
}

// FindIncrList 找到增量文件列表
func FindIncrList(full *BackupFileName, recoverTime uint32, fileObjList []*BackupFileName) ([]*BackupFileName, error) {
	if full.Version == BackupFileVersionV0 {
		return findIncrListV0(full, recoverTime, fileObjList)
	} else if full.Version == BackupFileVersionV1 {
		return findIncrListV1(full, recoverTime, fileObjList)
	} else {
		return nil, fmt.Errorf("Backup Version:%s", full.Version)
	}

}

// findIncrListV0 找到增量文件列表
func findIncrListV0(full *BackupFileName, recoverTime uint32, fileObjList []*BackupFileName) ([]*BackupFileName, error) {
	var incrList []*BackupFileName
	for _, file := range fileObjList {
		if file.Type != BackupTypeIncr {
			continue
		}
		if file.Version != BackupFileVersionV0 {
			continue
		}
		if file.V0FullStr == full.V0FullStr {
			incrList = append(incrList, file)
		}
	}

	//刚好回到全备的时间，不需要再导入INCR
	if full.LastTs.Sec == recoverTime {
		return nil, nil
	}

	if len(incrList) == 0 {
		// Ok
		if full.LastTs.Sec == recoverTime {
			return nil, nil
		} else {
			return nil, fmt.Errorf("INCR_NOT_FOUND")
		}
	}

	sort.Slice(incrList, func(i, j int) bool {
		return incrList[i].LastTs.Sec < incrList[j].LastTs.Sec
	})

	//回档目标时间 在 opLog文件中
	checkTsOk := false
	//回档Oplog列表正确
	checkSeqOk := true

	lastIncr := incrList[len(incrList)-1]
	checkTsOk = lastIncr.LastTs.Sec >= recoverTime
	log.Debugf("Check Max LastTs %d is >= recoverTime %d ? %v\n", lastIncr.LastTs.Sec, recoverTime, checkTsOk)

	if lastIncr.V0IncrSeq != uint32(len(incrList)) {
		checkSeqOk = false
		log.Debugf("Debug Bad Seq for INCR %s %d\n", lastIncr.FileName, lastIncr.V0IncrSeq)
	}

	for i := 0; i < len(incrList); i++ {
		if incrList[i].V0IncrSeq != uint32(i+1) {
			checkSeqOk = false
			log.Debugf("Debug Bad Seq for INCR %s %d\n", incrList[i].FileName, incrList[i].V0IncrSeq)
		}
	}

	if !checkSeqOk {
		return nil, fmt.Errorf("Bad Oplog FileList")
	}

	if !checkTsOk {
		return nil, fmt.Errorf("recoverTime gt lastIncr.LastTs")
	}

	// Delete Not Need INCR
	// PREV < recoverTime < NEXT ; drop NEXT + 1
	last := len(incrList) - 1
	for i := 0; i < len(incrList)-1; i++ {
		prev := incrList[i]
		if prev.LastTs.Sec >= recoverTime {
			last = i
			break
		}
	}

	last = last + 1
	return incrList[:last], nil
}

// findIncrListV1 找到增量文件列表
func findIncrListV1(full *BackupFileName, recoverTime uint32, fileObjList []*BackupFileName) ([]*BackupFileName, error) {
	var incrList []*BackupFileName

	for _, file := range fileObjList {
		if file.Type != BackupTypeIncr {
			continue
		}
		if file.Version != BackupFileVersionV1 {
			continue
		}

		// INCR LastTs 小于全备一致性时间 抛弃
		if file.LastTs.Sec < full.LastTs.Sec {
			continue
		}

		// INCR FirstTs 大于回档时间 抛弃
		if file.FirstTs.Sec > recoverTime {
			continue
		}

		incrList = append(incrList, file)
		fmt.Printf("append  INCR %s %+v %+v\n", file.FileName, file.FirstTs, file.LastTs)

	}

	if len(incrList) == 0 {
		// Ok
		if full.LastTs.Sec == recoverTime {
			return nil, nil
		} else {
			return nil, fmt.Errorf("INCR_NOT_FOUND")
		}
	}

	sort.Slice(incrList, func(i, j int) bool {
		return incrList[i].LastTs.Sec < incrList[j].LastTs.Sec
	})

	checkFirstTsOk := false
	checkLastTsOk := false
	checkSeqOk := true

	firstIncr := incrList[0]
	lastIncr := incrList[len(incrList)-1]

	checkFirstTsOk = firstIncr.FirstTs.Sec <= full.LastTs.Sec && firstIncr.LastTs.Sec >= full.LastTs.Sec
	checkLastTsOk = lastIncr.FirstTs.Sec <= recoverTime && lastIncr.LastTs.Sec >= recoverTime

	log.Debugf("check_first_ts_ok  %d>=%d && %d<=%d  ? %v\n",
		firstIncr.FirstTs.Sec, full.LastTs.Sec, firstIncr.LastTs.Sec, full.LastTs.Sec, checkLastTsOk)
	for i := 0; i < len(incrList)-1; i++ {
		prev := incrList[i]
		next := incrList[i+1]

		if !(prev.LastTs.Sec == next.FirstTs.Sec && prev.LastTs.I == next.FirstTs.I) {
			checkSeqOk = false
		}
	}

	if !checkFirstTsOk {
		return nil, fmt.Errorf("BadFirstTs")

	}
	if !checkLastTsOk {
		return nil, fmt.Errorf("BadLastTs")
	}

	if !checkSeqOk {
		return nil, fmt.Errorf("BadOplogList")
	}

	return incrList, nil

}
