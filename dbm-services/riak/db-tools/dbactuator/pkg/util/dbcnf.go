package util

import (
	"fmt"
	"os"
	"path"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"

	"github.com/pkg/errors"
	"gopkg.in/ini.v1"
)

const (
	// SecTag TODO
	SecTag = "sectag"
	// KeyTag TODO
	KeyTag = "keytag"
)

const (
	// MysqldSec TODO
	MysqldSec = "mysqld"
)

// CnfFile TODO
type CnfFile struct {
	FileName string
	Cfg      *ini.File
	mu       *sync.Mutex
}

// CnfUint TODO
type CnfUint struct {
	KvMap map[string]string
	// 可重复的key
	ShadowKvMap map[string]string
	// skip_symbolic_links单key的配置
	BoolKey []string
}

// MycnfIniObject TODO
type MycnfIniObject struct {
	Section map[string]*CnfUint
}

var iniLoadOption = ini.LoadOptions{
	PreserveSurroundedQuote: true,
	IgnoreInlineComment:     true,
	AllowBooleanKeys:        true,
	AllowShadows:            true,
}

// NewMyCnfObject  渲染模板全量的配置文件
//
//	@receiver c
//	@receiver myfileName
//	@return nf
//	@return err
func NewMyCnfObject(c interface{}, myfileName string) (nf *CnfFile, err error) {
	nf = NewEmptyCnfObj(myfileName)
	t := reflect.TypeOf(c)
	if t.Kind() != reflect.Struct {
		return nil, fmt.Errorf("mf reflect is not struct")
	}
	var isMysqldSectionExists bool      // 要求 mysqld section 存在
	for i := 0; i < t.NumField(); i++ { // 这里遍历的是 [map{client} map{mysqld} ...]
		var sectionName = t.Field(i).Tag.Get(SecTag)
		m := reflect.ValueOf(c).FieldByName(t.Field(i).Name)
		if _, err := nf.Cfg.NewSection(sectionName); err != nil {
			return nil, err
		}
		for _, k := range m.MapKeys() {
			if err = nf.RenderSection(sectionName, k.String(), m.MapIndex(k).String(), false); err != nil {
				return nil, err
			}
		}
		if sectionName == MysqldSec {
			isMysqldSectionExists = true
		}
	}
	if !isMysqldSectionExists {
		return nil, fmt.Errorf("must Include Sections [mysqld]")
	}
	return
}

// ReplaceMyconfigsObjects TODO
func ReplaceMyconfigsObjects(f *CnfFile, c interface{}) error {
	t := reflect.TypeOf(c)
	v := reflect.ValueOf(c)
	if t.Kind() != reflect.Struct {
		return fmt.Errorf("mycnf object reflect is not struct")
	}
	for i := 0; i < t.NumField(); i++ {
		var sectionName = t.Field(i).Tag.Get(SecTag)
		if v.Field(i).Type().Kind() == reflect.Struct {
			structField := v.Field(i).Type()
			for j := 0; j < structField.NumField(); j++ {
				keyName := structField.Field(j).Tag.Get(KeyTag)
				val := v.Field(i).Field(j).String()
				f.ReplaceValue(sectionName, string(keyName), false, val)
			}
		}
	}
	return nil
}

// NewEmptyCnfObj TODO
// NewCnfFile 生成ini empty 用于外部传参的配置中渲染新的my.cnf
//
//	@receiver mycnf
//	@return *CnfFile
//	@return error
func NewEmptyCnfObj(mycnf string) *CnfFile {
	return &CnfFile{
		FileName: mycnf,
		mu:       &sync.Mutex{},
		Cfg:      ini.Empty(iniLoadOption),
	}
}

// LoadMyCnfForFile 读取一个已经存在的配置文件，将配置文件的内容解析,用于程序读取、修改my.cnf
//
//	@receiver mycnf
//	@return *CnfFile
//	@return error
func LoadMyCnfForFile(mycnf string) (*CnfFile, error) {
	if err := cmutil.FileExistsErr(mycnf); err != nil {
		return nil, err
	}
	cfg, err := ini.LoadSources(iniLoadOption, mycnf)
	if err != nil {
		return nil, err
	}
	return &CnfFile{
		FileName: mycnf,
		mu:       &sync.Mutex{},
		Cfg:      cfg,
	}, nil
}

func newMyCnfUint() *CnfUint {
	return &CnfUint{
		KvMap:       make(map[string]string),
		ShadowKvMap: make(map[string]string),
		BoolKey:     make([]string, 0),
	}
}

// Load load m.FileName to CnfOj
func (m *CnfFile) Load() error {
	if obj, err := LoadMyCnfForFile(m.FileName); err != nil {
		return err
	} else {
		m.Cfg = obj.Cfg
		if m.mu == nil {
			m.mu = &sync.Mutex{}
		}
	}
	return nil
}

// GetMySQLDataDir 从my.cnf 获取datadir
//
//	@receiver m
//	@return datadir
//	@return err
//
// e.g: datadir=/data1/mysqldata/20000/data
func (m *CnfFile) GetMySQLDataDir() (datadir string, err error) {
	if m.Cfg.Section(MysqldSec).HasKey("datadir") {
		return filepath.Dir(m.Cfg.Section(MysqldSec).Key("datadir").String()), nil
	}
	return "", fmt.Errorf("在配置中没找到datadir的配置项")
}

// GetMySQLLogDir 从配置中获取mysql logdir
//
//	@receiver m
//	@return logdir
//	@return err
func (m *CnfFile) GetMySQLLogDir() (logdir string, err error) {
	// 先从 log_bin 配置项获取logdir
	// 但是可能存在历史的实例并没有开始binlog
	// log_bin = ON
	// log_bin_basename = /data/mysqllog/20000/binlog/binlog20000
	// log_bin_index    = /data/mysqllog/20000/binlog/binlog20000.index
	// 或者 log_bin      = /data/mysqllog/20000/binlog/binlog20000.bin
	// 或者 slow_query_log_file = /data/mysqllog/20000/slow-query.log
	keys := []string{"log_bin", "log_bin_basename", "slow_query_log_file"}

	for _, k := range keys {
		if val, err := m.GetMySQLCnfByKey(MysqldSec, k); err == nil {
			if filepath.IsAbs(val) {
				return val, nil
			}
		}
	}
	return "", fmt.Errorf("在配置中没找到 log_bin 的配置项")
}

// GetBinLogDir 获取 binlog dir
// 这里只从 my.cnf 获取，有可能没有设置选项，外部需要考虑再次从 global variables 获取
// 返回 binlog 目录和 binlog 文件名前缀
func (m *CnfFile) GetBinLogDir() (binlogDir, namePrefix string, err error) {
	// log_bin = ON
	// log_bin_basename = /data/mysqllog/20000/binlog/binlog20000 // binlog 在没有指定路径的情况下，默认存放在 datadir
	// log_bin_index    = /data/mysqllog/20000/binlog/binlog20000.index
	// 或者 log_bin      = /data/mysqllog/20000/binlog/binlog20000.bin
	keys := []string{"log_bin", "log_bin_basename"}
	for _, k := range keys {
		if val, err := m.GetMySQLCnfByKey(MysqldSec, k); err == nil {
			if filepath.IsAbs(val) {
				if binlogDir, namePrefix, err = m.ParseLogBinBasename(val); err == nil {
					return binlogDir, namePrefix, err
				}
			}
		}
	}
	return "", "", fmt.Errorf("binlog dir not found or parse failed")
}

// ParseLogBinBasename TODO
func (m *CnfFile) ParseLogBinBasename(val string) (binlogDir, namePrefix string, err error) {
	binlogDir, namePrefix = path.Split(val)
	if cmutil.IsDirectory(binlogDir) && !cmutil.IsDirectory(val) {
		if strings.Contains(namePrefix, ".") {
			binlogFilename := strings.Split(namePrefix, ".")
			namePrefix = binlogFilename[0]
		}
		return binlogDir, namePrefix, nil
	} else {
		logger.Error("expect %s is a dir and % is not dir", binlogDir, val)
	}
	errStr := fmt.Sprintf("%s is not a valid log_bin_basename", val)
	logger.Warn(errStr)
	return "", "", errors.New(errStr)
}

// GetRelayLogDir TODO
func (m *CnfFile) GetRelayLogDir() (string, error) {
	// relay-log = /data1/mysqldata/20000/relay-log/relay-log.bin
	// 或者 relay_log_basename = /data1/mysqldata/20000/relay-log/relay-bin
	keys := []string{"relay_log", "relay_log_basename"}
	for _, k := range keys {
		if val, err := m.GetMySQLCnfByKey(MysqldSec, k); err == nil {
			if filepath.IsAbs(val) { // 必须是绝对路径
				return val, nil
			}
		}
	}
	return "", fmt.Errorf("在配置中没找到 relay 的配置项")
}

// GetMySQLSocket 从my.cnf中获取socket value
//
//	@receiver m
//	@return socket
//	@return err
func (m *CnfFile) GetMySQLSocket() (socket string, err error) {
	if m.Cfg.Section(MysqldSec).HasKey("socket") {
		return m.Cfg.Section(MysqldSec).Key("socket").String(), nil
	}
	return "", fmt.Errorf("在配置中没找到socket的配置项")
}

// GetMySQLCnfByKey 从 my.cnf 获取 key 对应的 value
// 允许替换 _, -
// 如果 section 为空，会尝试从 key 中以 . 切分 section
func (m *CnfFile) GetMySQLCnfByKey(section, key string) (string, error) {
	if section == "" {
		sk := GetSectionFromKey(key, false)
		key = sk.Key
		section = sk.Section
	}
	key = m.GetKeyFromFile(section, key)
	if m.Cfg.Section(section).HasKey(key) {
	} else {
		return "", fmt.Errorf("在配置中没找到 %s 的配置项", key)
	}
	return m.Cfg.Section(section).Key(key).String(), nil
}

// GetMyCnfByKeyWithDefault TODO
func (m *CnfFile) GetMyCnfByKeyWithDefault(section, key string, valueDefault string) string {
	if val, err := m.GetMySQLCnfByKey(section, key); err != nil {
		return valueDefault
	} else {
		return val
	}
}

// GetProxyLogFilePath  获取 Proxy log-file 的value
//
//	@receiver m
//	@return logFile
//	@return err
func (m *CnfFile) GetProxyLogFilePath() (logFile string, err error) {
	if m.Cfg.Section("mysql-proxy").HasKey("log-file") {
		return m.Cfg.Section("mysql-proxy").Key("log-file").String(), nil
	}
	return "", fmt.Errorf("在配置中没找到log-file的配置项")
}

// SaveMySQLConfig2Object 将 my.cnf 变成 key map
func (m *CnfFile) SaveMySQLConfig2Object() MycnfIniObject {
	var object MycnfIniObject
	object.Section = make(map[string]*CnfUint)
	for _, section := range m.Cfg.SectionStrings() {
		object.Section[section] = newMyCnfUint()
		for _, keyName := range m.Cfg.Section(section).KeyStrings() {
			if kv, err := m.Cfg.Section(section).GetKey(keyName); err == nil {
				object.Section[section].KvMap[keyName] = kv.Value()
			}
		}
	}
	return object
}

// FastSaveChange 快速修改一个配置项，并持久化到文件
func (m *CnfFile) FastSaveChange(port int, section, key, value string) (err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	// 假如删除一个不存在的Key,不会抛出异常
	m.Cfg.Section(section).DeleteKey(key)
	if _, err = m.Cfg.Section(section).NewKey(key, value); err != nil {
		return
	}
	err = m.Cfg.SaveTo(fmt.Sprintf("my.cnf.%d", port))
	return
}

// SafeSaveFile 全量持久化配置文件
func (m *CnfFile) SafeSaveFile(isProxy bool) (err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	nf, err := m.sortAllkeys(isProxy)
	if err != nil {
		return err
	}
	err = nf.Cfg.SaveTo(m.FileName)
	return
}

// sortAllkeys 对写入的key进行排序
//
//	@receiver m
//	@return *CnfFile
//	@return error
func (m *CnfFile) sortAllkeys(isProxy bool) (*CnfFile, error) {
	f := CnfFile{
		Cfg: ini.Empty(iniLoadOption),
		mu:  &sync.Mutex{},
	}
	for _, sec := range m.Cfg.Sections() {
		secName := sec.Name()
		if _, err := f.Cfg.NewSection(secName); err != nil {
			return nil, err
		}
		keys := m.Cfg.Section(secName).KeyStrings()
		sort.Strings(keys)
		for _, key := range keys {
			if m.isShadowKey(key) {
				for _, val := range m.Cfg.Section(secName).Key(key).ValueWithShadows() {
					f.RenderSection(secName, key, val, isProxy)
				}
			}
			f.RenderSection(secName, key, m.Cfg.Section(secName).Key(key).Value(), isProxy)
		}
	}
	return &f, nil
}

// isShadowKey TODO
// 表示下面的key,可以在配置文件重复出现
func (m *CnfFile) isShadowKey(key string) bool {
	key = strings.ReplaceAll(key, "-", "_")
	sk := []string{
		"replicate_do_db", "replicate_ignore_db", "replicate_do_table", "replicate_wild_do_table",
		"replicate_ignore_table", "replicate_wild_ignore_table",
	}
	return cmutil.HasElem(key, sk)
}

// GetInitDirItemTpl TODO
func (m *CnfFile) GetInitDirItemTpl(initDirs map[string]string) (err error) {
	mysqld, err := m.Cfg.GetSection(MysqldSec)
	if err != nil {
		return
	}
	for key := range initDirs {
		initDirs[key] = mysqld.Key(key).String()
	}
	return
}

// RenderSection 替换渲染配置,proxy keepalive=true 不能和mysql的bool一样进行渲染
//
//	@receiver f
//	@receiver sectionName
//	@receiver key
//	@receiver val
//	@receiver isProxy
//	@return err
func (m *CnfFile) RenderSection(sectionName, key, val string, isProxy bool) (err error) {
	if m.isShadowKey(key) {
		for _, shadowv := range strings.Split(val, ",") {
			if _, err := m.Cfg.Section(sectionName).NewKey(key, shadowv); err != nil {
				return err
			}
			fmt.Println(",", "M")
		}
		return nil
	}
	//	proxy.cnf 需要渲染 boolkey
	//	my.cnf 如果是空值，当做boolkey处理
	if !isProxy {
		if strings.TrimSpace(val) == "true" {
			if _, err = m.Cfg.Section(sectionName).NewBooleanKey(key); err != nil {
				return err
			}
			return nil
		}
	}
	// 如果是不是空值，当做boolkey处理
	if _, err = m.Cfg.Section(sectionName).NewKey(key, val); err != nil {
		return err
	}
	return nil
}

// ReplaceKeyName 存在oldkey，则替换为newkey; 不存在oldkey，则作任何处理
// 比如用在把 default_charset_server 替换成 default-charset-server 的场景
func (m *CnfFile) ReplaceKeyName(section string, oldKey string, newKey string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	sel := m.Cfg.Section(section)
	if sel.HasKey(oldKey) {
		k, _ := sel.GetKey(oldKey)
		sel.NewKey(newKey, k.Value())
		sel.DeleteKey(oldKey)
	}
}

// ReplaceMoreKv TODO
func (m *CnfFile) ReplaceMoreKv(pairs map[string]CnfUint) error {
	if len(pairs) <= 0 {
		return nil
	}
	for section, mu := range pairs {
		for k, v := range mu.KvMap {
			m.ReplaceValue(section, k, false, v)
		}
	}
	return nil
}

// GetKeyFromFile godoc
// my.cnf 里面允许 _, - 两种分隔符的变量，获取或者替换时，需要两种都尝试获取
func (m *CnfFile) GetKeyFromFile(section string, key string) string {
	if !m.Cfg.Section(section).HasKey(key) {
		oldKey := key
		key = strings.ReplaceAll(key, "_", "-")
		if !m.Cfg.Section(section).HasKey(key) {
			key = strings.ReplaceAll(key, "-", "_")
			if !m.Cfg.Section(section).HasKey(key) {
				key = oldKey // 始终没找到 key, 恢复输入值
			}
		}
	}
	return key
}

// ReplaceValue kv不存在则写入，k存在则更新
// 会判断是否是 shadowKey
// 如果 key 不存在会尝试替换 _ 成 -
func (m *CnfFile) ReplaceValue(section string, key string, isBool bool, value string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	key = m.GetKeyFromFile(section, key)
	if !m.isShadowKey(key) {
		m.Cfg.Section(section).DeleteKey(key)
	}
	if isBool {
		m.Cfg.Section(section).NewBooleanKey(key)
		return
	}
	m.Cfg.Section(section).NewKey(key, value)
}

// UpdateKeyValue 修改一个配置项，会判断是否是 shadowKey
func (m *CnfFile) UpdateKeyValue(section, key, value string) (err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.isShadowKey(key) {
		// 如果这些key 是可重复的key
		err = m.Cfg.Section(section).Key(key).AddShadow(value)
		return
	}
	m.Cfg.Section(section).Key(key).SetValue(value)
	return
}

// GetMyCnfFileName 获取默认 my.cnf 的路径，不检查是否存在
func GetMyCnfFileName(port int) string {
	return fmt.Sprintf("%s.%d", cst.DefaultMyCnfName, port)
}

// GetProxyCnfName TODO
/**
 * @description: 计算proxy cnf name
 * @receiver {int} port
 * @return {*}
 */
func GetProxyCnfName(port int) string {
	return fmt.Sprintf("%s.%d", cst.DefaultProxyCnfName, port)
}

// ReplaceValuesToFile 文本替换 my.cnf 里面的 value，如果 key 不存在则插入 [mysqld] 后面
func (m *CnfFile) ReplaceValuesToFile(newItems map[string]string) error {
	f, err := os.ReadFile(m.FileName)
	if err != nil {
		return err
	}
	lines := strings.Split(string(f), "\n")
	itemsNotFound := make(map[string]string)
	for i, lineText := range lines {
		for k, v := range newItems {
			itemsNotFound[k] = v
			reg := regexp.MustCompile(fmt.Sprintf(`^\s*%s\s*=(.*)`, k))
			if reg.MatchString(lineText) {
				lines[i] = fmt.Sprintf(`%s = %s`, k, v)
				delete(itemsNotFound, k) // found
			}
		}
	}
	for k, v := range itemsNotFound {
		StringsInsertAfter(lines, "[mysqld]", fmt.Sprintf(`%s = %s`, k, v))
	}
	if err = os.WriteFile(m.FileName, []byte(strings.Join(lines, "\n")), 0644); err != nil {
		return err
	}
	return nil
}

// GetMysqldKeyVaule 增加基础方法，获取myconf上面的某个配置参数值，用于做前置校验的对比
func (m *CnfFile) GetMysqldKeyVaule(keyName string) (value string, err error) {
	mysqld, err := m.Cfg.GetSection(MysqldSec)
	if err != nil {
		return "", err
	}
	return mysqld.Key(keyName).String(), nil
}

// CnfKey my.cnf key格式
type CnfKey struct {
	Section   string
	Key       string
	IsBool    bool
	Separator string
}

// GetSectionFromKey 从 . 分隔符里分离 section, key
// replace 控制是否将 - 替换为 _ (set global 用)
func GetSectionFromKey(key string, replace bool) *CnfKey {
	sk := &CnfKey{Separator: "."}
	ss := strings.Split(key, sk.Separator)
	if len(ss) == 2 {
		sk.Section = ss[0]
		sk.Key = ss[1]
	} else {
		sk.Section = ""
		sk.Key = key
	}
	if replace {
		sk.Key = strings.ReplaceAll(sk.Key, "-", "_")
	}
	return sk
}

// MycnfItemsMap mysqld变量映射到 my.cnf 中的配置名
var MycnfItemsMap = map[string]string{
	"time_zone":            "default-time-zone",
	"character_set_system": "character_set_server",
}

// CreateExporterConf 简单写一个根据端口号生成exporter文件的方法
func CreateExporterConf(fileName string, host string, port string, user string, password string) (err error) {
	cnfPath := fmt.Sprintf("%s", fileName)
	cfg := ini.Empty()

	exporterSection, err := cfg.NewSection("client")
	if err != nil {
		return err
	}
	exporterSection.NewKey("user", user)
	exporterSection.NewKey("password", password)
	exporterSection.NewKey("host", host)
	exporterSection.NewKey("port", port)
	err = cfg.SaveTo(cnfPath)
	if err != nil {
		return err
	}
	return nil
}
