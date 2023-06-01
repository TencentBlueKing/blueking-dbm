// Package osutil TODO
package osutil

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"math"
	"math/rand"
	"net"
	"os"
	"os/exec"
	"os/user"
	"path"
	"path/filepath"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode"

	"dbm-services/common/go-pubpkg/logger"

	"github.com/dustin/go-humanize"
	"github.com/pkg/errors"
)

// Ucfirst TODO
func Ucfirst(str string) string {
	for i, v := range str {
		return string(unicode.ToUpper(v)) + str[i+1:]
	}
	return ""
}

// HasElem TODO
func HasElem(elem interface{}, slice interface{}) bool {
	defer func() {
		if err := recover(); err != nil {
			logger.Error("HasElem error %s", err)
		}
	}()
	arrV := reflect.ValueOf(slice)
	if arrV.Kind() == reflect.Slice || arrV.Kind() == reflect.Array {
		for i := 0; i < arrV.Len(); i++ {
			// XXX - panics if slice element points to an unexported struct field
			// see https://golang.org/pkg/reflect/#Value.Interface
			if reflect.DeepEqual(arrV.Index(i).Interface(), elem) {
				return true
			}
		}
	}
	return false
}

// 描述：
// 把任何类型的值转换成字符串类型
// 目前暂时支持的类型为：string,int,int64,float64,bool

// ChangeValueToString TODO
func ChangeValueToString(value interface{}) (string, error) {
	var result string
	if item, ok := value.(string); ok {
		result = item
	} else if item1, ok := value.(int); ok {
		result = strconv.Itoa(item1)
	} else if item2, ok := value.(int64); ok {
		result = strconv.FormatInt(item2, 10)
	} else if item3, ok := value.(float64); ok {
		result = strconv.FormatFloat(item3, 'f', -1, 64)
	} else if item4, ok := value.(bool); ok {
		result = strconv.FormatBool(item4)
	} else {
		return result, errors.New("[ChangeValueToString]value type unknow,not in (string,int,int64,float64,bool)")
	}
	return result, nil
}

// GetLocalIP 获得本地IP
func GetLocalIP() (string, error) {
	var localIP string
	var err error
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		return localIP, err
	}
	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				localIP = ipnet.IP.String()
				return localIP, nil
			}
		}
	}
	err = fmt.Errorf("can't find local ip")
	return localIP, err
}

// StringToMap 字符串 TO map
// 如db1,,db2,db3,db2 ,等去重并转换成db1,db2,db3
func StringToMap(srcStr string, seq string) map[string]struct{} {
	splitReg := regexp.MustCompile(seq)
	strList := splitReg.Split(srcStr, -1)
	strMap := make(map[string]struct{})
	for _, str := range strList {
		if len(strings.TrimSpace(str)) == 0 {
			continue
		}
		strMap[strings.TrimSpace(str)] = struct{}{}
	}
	return strMap
}

// StrSliceToMap 字符串slice to map,目标是去重
func StrSliceToMap(srcStrSlice []string) map[string]struct{} {
	strMap := make(map[string]struct{})
	for _, str := range srcStrSlice {
		if len(strings.TrimSpace(str)) == 0 {
			continue
		}
		strMap[strings.TrimSpace(str)] = struct{}{}
	}
	return strMap
}

// MapKeysToSlice TODO
func MapKeysToSlice(mapObj map[string]struct{}) []string {
	keys := make([]string, len(mapObj))

	i := 0
	for k := range mapObj {
		keys[i] = k
		i++
	}
	return keys
}

// IntnRange TODO
func IntnRange(min, max int) int {
	rand.Seed(time.Now().Unix())
	return rand.Intn(max-min) + min
}

// GetFileModifyTime TODO
func GetFileModifyTime(filename string) (bool, int64) {
	if _, err := os.Stat(filename); !os.IsNotExist(err) {
		f, err1 := os.Open(filename)
		if err1 != nil {
			return true, 0
		}
		fi, err2 := f.Stat()
		if err2 != nil {
			return true, 0
		}
		return true, fi.ModTime().Unix()
	}
	return false, 0
}

// GetMySQLBaseDir TODO
func GetMySQLBaseDir(grepstr string) (string, error) {
	strCmd := fmt.Sprintf(`ps -ef | grep 'mysqld '|grep basedir | grep %s| grep -v grep`, grepstr)
	data, err := ExecShellCommand(false, strCmd)
	reg := regexp.MustCompile(`--basedir=[/A-Za-z_]*`)
	tmparr := reg.FindAllString(data, -1)
	if len(tmparr) != 1 {
		return "", errors.New("get basedir unexpected")
	}
	basedir := strings.Split(strings.TrimSpace(tmparr[0]), "=")
	if len(basedir) != 2 || strings.TrimSpace(basedir[1]) == "" {
		return "", fmt.Errorf("get base dir error:%v", basedir)
	}
	return strings.TrimSpace(basedir[1]), err
}

// GetMySQLBinDir TODO
func GetMySQLBinDir(getstr string) (string, error) {
	basedir, err := GetMySQLBaseDir(getstr)
	if err != nil {
		return "", err
	}
	if !strings.HasPrefix(basedir, "/") {
		return "", fmt.Errorf("basedir must start at /")
	}
	return strings.TrimRight(basedir, "/") + "/bin", nil
}

// MakeSoftLink src and dest are absolute path with filename
func MakeSoftLink(src string, dest string, force bool) error {
	if !FileExist(src) {
		return errors.Errorf("src file does not exists: %s", src)
	}
	if src == dest {
		return nil
	}
	if FileExist(dest) {
		if !force {
			return errors.Errorf("dest file exists: %s", dest)
		}
		if err := os.Remove(dest); err != nil {
			logger.Warn("remove file %s failed, err:%s", dest, err.Error())
		}
	}
	// os.Symlink(src, dest)
	cmd := exec.Command("ln", "-s", src, dest)
	out, err := cmd.CombinedOutput()
	if err != nil {
		logger.Error("ln -s failed, output:%s, err:%s", string(out), err.Error())
	}
	return err
}

// MakeHardLink TODO
func MakeHardLink(src string, dest string) error {
	if !FileExist(src) {
		return errors.New("src file does not exists")
	} else if FileExist(dest) {
		return errors.New("dest file already exists")
	}
	if err := os.Link(src, dest); err != nil {
		return err
	}
	return nil
}

// CheckFileExistWithPath TODO
func CheckFileExistWithPath(filename, dirname string) bool {
	var destFile string
	if strings.HasPrefix(filename, "/") {
		destFile = filename
	} else {
		destFile = fmt.Sprintf(`%s/%s`, dirname, filename) // app_149/ulog/xxxx.ulog
	}

	if _, err := os.Stat(destFile); err != nil {
		if os.IsNotExist(err) {
			return false
		}
		return false
	}
	return true
}

// CheckAndMkdir mkdir ppathname/pathname
func CheckAndMkdir(pathname, ppathname string) error {
	if !CheckFileExistWithPath(pathname, ppathname) {
		return os.MkdirAll(ppathname+"/"+pathname, 0755)
	}
	return nil
}

// ParsePsOutput TODO
// for ps command, output should skip first line, which
// refer to cmd string itself(catch by ps after bash -c)
func ParsePsOutput(rawOutput string) string {
	var output []string
	lines := strings.Split(rawOutput, "\n")
	for i, line := range lines {
		// skip headers
		if i == 0 {
			continue
		}

		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		output = append(output, fields[0])
	}
	return strings.Join(output, "\n")
}

// FileExist TODO
func FileExist(fileName string) bool {
	_, err := os.Stat(fileName)
	if err != nil {
		if os.IsExist(err) {
			return true
		}
		return false
	}
	return true
}

// GetFileMd5 TODO
func GetFileMd5(file string) (string, error) {
	cmd := "md5sum " + file
	data, err := exec.Command("/bin/bash", "-c", cmd).CombinedOutput()
	if err != nil {
		return "", err
	}
	reg, err := regexp.Compile(`\s+`)
	if err != nil {
		return "", err
	}
	array := reg.Split(string(data), -1)
	if len(array) != 3 {
		return "", errors.New("data result len wrong ,not 3,is " + strconv.Itoa(len(array)))
	}
	return array[0], nil
}

// GetLinuxDisksInfo TODO
func GetLinuxDisksInfo() ([]DiskInfo, error) {
	var res []DiskInfo
	cmd := "df -l|grep -vE 'Filesystem|overlay|tmpfs'"
	data, err := exec.Command("/bin/bash", "-c", cmd).CombinedOutput()
	if err != nil {
		return res, err
	}
	reg, err := regexp.Compile(`\n+`)
	if err != nil {
		return res, err
	}
	strs := reg.Split(string(data), -1)

	for _, row := range strs {
		if strings.TrimSpace(row) == "" {
			continue
		}
		result := DiskInfo{}
		reg, err := regexp.Compile(`\s+`)
		if err != nil {
			return res, err
		}
		array := reg.Split(row, -1)
		if len(array) == 6 {
			result.Filesystem = array[0]
			result.Blocks_1K = array[1]
			result.Used, err = strconv.Atoi(array[2])
			if err != nil {
				return res, err
			}
			result.Available, err = strconv.ParseInt(array[3], 10, 64)
			if err != nil {
				return res, err
			}
			result.UsedRate = array[4]
			result.MountedOn = array[5]

			res = append(res, result)
		} else {
			return res, errors.New("data result len wrong ,not 6,is " + strconv.Itoa(len(array)))
		}
	}

	return res, nil
}

// GetCurrentUser TODO
func GetCurrentUser() (string, error) {
	var currentUser = ""
	cmd := `whoami`
	data, err := exec.Command("/bin/bash", "-c", cmd).CombinedOutput()
	if err != nil {
		return currentUser, fmt.Errorf(err.Error() + ",cmd:" + cmd)
	}
	reg, err := regexp.Compile(`\n+`)
	if err != nil {
		return currentUser, err
	}
	array := reg.Split(string(data), -1)
	if len(array) == 2 {
		currentUser = array[0]
	} else {
		return currentUser, fmt.Errorf("get currentUser fail,len not 2,array:%s", strings.Join(array, ";"))
	}

	return currentUser, nil
}

// GetLinuxDirDiskInfo TODO
func GetLinuxDirDiskInfo(dir string) (DiskInfo, error) {
	result := DiskInfo{}
	cmd := fmt.Sprintf("df -l %s|grep -v Filesystem", dir)
	data, err := exec.Command("/bin/bash", "-c", cmd).CombinedOutput()
	if err != nil {
		return result, err
	}
	reg, err := regexp.Compile(`\s+`)
	if err != nil {
		return result, err
	}
	array := reg.Split(string(data), -1)
	if len(array) == 7 {
		result.Filesystem = array[0]
		result.Blocks_1K = array[1]
		result.Used, err = strconv.Atoi(array[2])
		if err != nil {
			return result, err
		}
		result.Available, err = strconv.ParseInt(array[3], 10, 64)
		if err != nil {
			return result, err
		}
		result.UsedRate = array[4]
		result.MountedOn = array[5]
	} else {
		return result, errors.New("data result len wrong ,not 7,is " + strconv.Itoa(len(array)))
	}

	return result, nil
}

// DiskInfo TODO
type DiskInfo struct {
	Filesystem string `json:"filesystem"`
	Blocks_1K  string `json:"blocks_1K"`
	Used       int    `json:"used"`
	Available  int64  `json:"available"`
	UsedRate   string `json:"usedRate"`
	MountedOn  string `json:"MountedOn"`
}

// SplitName 切分用户传过来的IP字符串列表等
// 切分规则：
// 把\r+|\s+|;+|\n+|,+这些分隔符，转成字符串数组
// 返回字符串数组
func SplitName(input string) ([]string, error) {
	if reg, err := regexp.Compile(`\r+|\s+|;+|\n+`); err != nil {
		return nil, err
	} else {
		input = reg.ReplaceAllString(input, ",")
	}
	if reg, err := regexp.Compile(`^,+|,+$`); err != nil {
		return nil, err
	} else {
		input = reg.ReplaceAllString(input, "")
	}
	if reg, err := regexp.Compile(`,+`); err != nil {
		return nil, err
	} else {
		input = reg.ReplaceAllString(input, ",")
	}
	result := strings.Split(input, ",")
	return result, nil
}

// Uniq 对字符串数组进行去重
func Uniq(input []string) []string {
	var newData []string
	if len(input) > 0 {
		temp := map[string]bool{}
		for _, value := range input {
			temp[value] = true
		}
		for k := range temp {
			newData = append(newData, k)
		}
	}
	return newData
}

// GetUidGid TODO
func GetUidGid(osuser string) (int, int, error) {
	group, err := user.Lookup(osuser)
	if err != nil {
		logger.Info("Failed to lookup user %s", osuser)
		return 0, 0, err
	}

	uid, err := strconv.Atoi(group.Uid)
	if err != nil {
		logger.Info("Convert Uid for %s : `%s` failed", osuser, group.Uid)
		return 0, 0, err
	}

	gid, err := strconv.Atoi(group.Gid)
	if err != nil {
		logger.Info("Convert Gid for %s : `%s` failed", osuser, group.Gid)
		return 0, 0, err
	}

	return uid, gid, err
}

// FileLineCounter 计算文件行数
// 参考: https://stackoverflow.com/questions/24562942/golang-how-do-i-determine-the-number-of-lines-in-a-file-efficiently
func FileLineCounter(filename string) (lineCnt uint64, err error) {
	_, err = os.Stat(filename)
	if err != nil && os.IsNotExist(err) {
		return 0, fmt.Errorf("file:%s not exists", filename)
	}
	file, err := os.Open(filename)
	if err != nil {
		return 0, fmt.Errorf("file:%s open fail,err:%w", filename, err)
	}
	defer func() {
		if err := file.Close(); err != nil {
			logger.Warn("close file %s failed, err:%s", filename, err.Error())
		}
	}()
	reader01 := bufio.NewReader(file)
	buf := make([]byte, 32*1024)
	lineCnt = 0
	lineSep := []byte{'\n'}

	for {
		c, err := reader01.Read(buf)
		lineCnt += uint64(bytes.Count(buf[:c], lineSep))

		switch {
		case err == io.EOF:
			return lineCnt, nil

		case err != nil:
			return lineCnt, fmt.Errorf("file:%s read fail,err:%w", filename, err)
		}
	}
}

// WrapFileLink TODO
func WrapFileLink(link string) string {
	name := filepath.Base(link)
	return fmt.Sprintf(`<a target="_blank" href="%s" class="link-item">%s</a>`, link, name)
}

// SetOSUserPassword run set user password by chpasswd
func SetOSUserPassword(user, password string) error {
	exec.Command("/bin/bash", "-c", "")
	cmd := exec.Command("chpasswd")
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("new pipe failed, err:%w", err)
	}
	go func() {
		_, err := io.WriteString(stdin, fmt.Sprintf("%s:%s", user, password))
		if err != nil {
			logger.Warn("write into pipe failed, err:%s", err.Error())
		}
		if err := stdin.Close(); err != nil {
			logger.Warn("colse stdin failed, err:%s", err.Error())
		}
	}()
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("run chpasswd failed, output:%s, err:%w", string(output), err)
	}
	return nil
}

// GetNumaStr TODO
func GetNumaStr() string {
	numaCmd := "numactl --show | grep policy"
	output, err := ExecShellCommand(false, numaCmd)
	if err != nil {
		logger.Error(err.Error())
		return ""
	}
	if len(output) > 0 {
		return "numactl --interleave=all "
	}
	return ""
}

// SafeRmDir TODO
func SafeRmDir(dir string) (err error) {
	if strings.TrimSpace(dir) == "/" {
		return fmt.Errorf("禁止删除系统根目录")
	}
	return os.RemoveAll(dir)
}

func getFileSize(f string) (int64, error) {
	fd, err := os.Stat(f)
	if err != nil {
		return 0, err
	}
	return fd.Size(), nil
}

// CalcFileSizeIncr TODO
func CalcFileSizeIncr(f string, secs uint64) string {
	var err error
	var t1Size, t2Size int64
	if t1Size, err = getFileSize(f); err != nil {
		return "0"
	}
	time.Sleep(time.Duration(secs) * time.Second)
	if t2Size, err = getFileSize(f); err != nil {
		return "0"
	}

	bytesIncr := uint64(math.Abs(float64(t2Size-t1Size))) / secs
	return humanize.Bytes(bytesIncr)
}

// PrintFileSizeIncr 后台计算文件变化
// ch 通知退出，外层需要 close(ch)
// 2 hour 超时
func PrintFileSizeIncr(
	f string, secs uint64, printInterval uint64,
	output func(format string, args ...interface{}), ch chan int,
) {
	for true {
		speed := CalcFileSizeIncr(f, secs)
		if speed != "0" {
			output("file %s change speed %s", f, speed)
		} else {
			break
		}
		select {
		case _, beforeClosed := <-ch:
			if !beforeClosed {
				return
			}
		case <-time.After(2 * time.Hour):
			return
		default:
			time.Sleep(time.Duration(printInterval) * time.Second)
		}
		/*
			ch <- 1 // 这里为了不阻塞，我们只关注外面的 close 信号
			if _, beforeClosed := <-ch; !beforeClosed {
				return
			}
		*/
	}
}

// CapturingPassThroughWriter is a writer that remembers
// data written to it and passes it to w
type CapturingPassThroughWriter struct {
	buf bytes.Buffer
	w   io.Writer
}

// NewCapturingPassThroughWriter creates new CapturingPassThroughWriter
func NewCapturingPassThroughWriter(w io.Writer) *CapturingPassThroughWriter {
	return &CapturingPassThroughWriter{
		w: w,
	}
}

// Write 用于常见IO
func (w *CapturingPassThroughWriter) Write(d []byte) (int, error) {
	w.buf.Write(d)
	return w.w.Write(d)
}

// Bytes returns bytes written to the writer
func (w *CapturingPassThroughWriter) Bytes() []byte {
	return w.buf.Bytes()
}

// ReadFileString TODO
func ReadFileString(filename string) (string, error) {
	if body, err := os.ReadFile(filename); err != nil {
		return "", err
	} else {
		return string(body), nil
	}
}

// CreateSoftLink TODO
// sourceFile : 绝对路径
// linkName: 觉得路径
func CreateSoftLink(sourceFile string, linkFile string) (err error) {
	if !(path.IsAbs(sourceFile) && path.IsAbs(linkFile)) {
		return fmt.Errorf("源文件和目标链接文件传参必须是绝对路径")
	}
	// try del origin link file
	if FileExist(linkFile) {
		if err := os.Remove(linkFile); err != nil {
			logger.Error("del %s failed", linkFile)
			return err
		}
	}
	return os.Symlink(sourceFile, linkFile)
}
