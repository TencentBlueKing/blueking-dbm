package syntax

import (
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/pkg/util"
	"fmt"
	"regexp"
	"strings"
)

// SpiderChecker TODO
func (c CreateTableResult) SpiderChecker(spiderVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	r.Parse(SR.SpiderCreateTableRule.CreateTbLike, !c.IsCreateTableLike, "")
	r.Parse(SR.SpiderCreateTableRule.CreateWithSelect, !c.IsCreateTableSelect, "")
	r.Parse(SR.SpiderCreateTableRule.ColChasetNotEqTbChaset, c.ColCharsetEqTbCharset(), "")
	ilegal, msg := c.ValidateSpiderComment()
	r.Parse(SR.SpiderCreateTableRule.IllegalComment, ilegal, msg)
	// comment 合法且非空
	if ilegal {
		b_shardKeyIsIndex := c.ShardKeyIsIndex()
		r.Parse(SR.SpiderCreateTableRule.ShardKeyNotIndex, b_shardKeyIsIndex, "")
		if !b_shardKeyIsIndex {
			r.Parse(SR.SpiderCreateTableRule.ShardKeyNotPk, c.ShardKeyIsNotPrimaryKey(), "")
		}
	}
	return
}

// Checker TODO
func (c CreateTableResult) Checker(mysqlVersion string) (r *CheckerResult) {
	r = &CheckerResult{}
	r.Parse(R.CreateTableRule.SuggestEngine, c.GetEngine(), "")
	r.Parse(R.CreateTableRule.SuggestBlobColumCount, c.BlobColumCount(), "")
	// 检查表名规范
	// R.CreateTableRule.NormalizedName指明yaml文件中的键，根据键获得item 进而和 val比较
	etypesli, charsli := NameCheck(c.TableName, mysqlVersion)
	for i, etype := range etypesli {
		r.Parse(R.CreateTableRule.NormalizedName, etype, charsli[i])
	}
	return
}

// BlobColumCount TODO
// ExceedMaxBlobColum 检查创建表时blob/text字段最大数，是否超过
func (c CreateTableResult) BlobColumCount() (blobColumCount int) {
	for _, v := range c.CreateDefinitions.ColDefs {
		if v.Type == "blob" {
			blobColumCount++
		}
	}
	logger.Info("blobColumCount:%d", blobColumCount)
	return
}

// ShardKeyIsIndex TODO
func (c CreateTableResult) ShardKeyIsIndex() bool {
	cmt := c.GetComment()
	if cmutil.IsEmpty(cmt) {
		return len(c.CreateDefinitions.KeyDefs) > 0
	}
	if !strings.Contains(cmt, "shard_key") {
		return true
	}
	sk, err := util.ParseGetShardKeyForSpider(cmt)
	if err != nil {
		logger.Error("parse get shardkey %s", err.Error())
		return false
	}
	for _, v := range c.CreateDefinitions.KeyDefs {
		for _, k := range v.KeyParts {
			if strings.Compare(k.ColName, sk) == 0 {
				return true
			}
		}
	}
	return false
}

// ShardKeyIsNotPrimaryKey TODO
func (c CreateTableResult) ShardKeyIsNotPrimaryKey() bool {
	cmt := c.GetComment()
	logger.Info("will check %s ,ShardKeyIsNotPrimaryKey", cmt)
	if cmutil.IsEmpty(cmt) {
		return true
	}
	if !strings.Contains(cmt, "shard_key") {
		return true
	}
	logger.Info("will check xaxsasxaxax ")
	sk, err := util.ParseGetShardKeyForSpider(cmt)
	if err != nil {
		logger.Error("parse get shardkey %s", err.Error())
		return false
	}
	for _, v := range c.CreateDefinitions.ColDefs {
		if v.PrimaryKey {
			logger.Info("get sk %s,pk:%s", sk, v.ColName)
			if strings.Compare(sk, v.ColName) == 0 {
				return true
			}
		}
	}
	return false
}

// GetValFromTbOptions TODO
func (c CreateTableResult) GetValFromTbOptions(key string) (val string) {
	for _, tableOption := range c.TableOptions {
		if tableOption.Key == key {
			val = tableOption.Value.(string)
		}
	}
	logger.Info("%s:%s", key, val)
	return val
}

// GetEngine TODO
func (c CreateTableResult) GetEngine() (engine string) {
	if v, ok := c.TableOptionMap["engine"]; ok {
		return v.(string)
	}
	return ""
}

// GetComment TODO
// comment
func (c CreateTableResult) GetComment() (engine string) {
	if v, ok := c.TableOptionMap["comment"]; ok {
		return v.(string)
	}
	return ""
}

// GetTableCharset TODO
// character_set
func (c CreateTableResult) GetTableCharset() (engine string) {
	if v, ok := c.TableOptionMap["character_set"]; ok {
		return v.(string)
	}
	return ""
}

// ValidateSpiderComment TODO
func (c CreateTableResult) ValidateSpiderComment() (bool, string) {
	comment := c.GetComment()
	if cmutil.IsEmpty(comment) {
		return true, ""
	}
	ret := util.ParseGetSpiderUserComment(comment)
	switch ret {
	case 0:
		return true, "OK"
	case 1:
		return false, "SQL CREATE TABLE WITH ERROR TABLE COMMENT"
	case 2:
		return false, "UNSUPPORT CREATE TABLE WITH ERROR COMMENT"
	}
	return false, ""
}

// GetAllColCharsets TODO
func (c CreateTableResult) GetAllColCharsets() (charsets []string) {
	for _, colDef := range c.CreateDefinitions.ColDefs {
		if !cmutil.IsEmpty(colDef.CharacterSet) {
			charsets = append(charsets, colDef.CharacterSet)
		}
	}
	return cmutil.RemoveDuplicate(charsets)
}

// ColCharsetEqTbCharset TODO
func (c CreateTableResult) ColCharsetEqTbCharset() bool {
	colCharsets := c.GetAllColCharsets()
	fmt.Println("colCharsets", colCharsets, len(colCharsets))
	if len(colCharsets) == 0 {
		return true
	}
	if len(colCharsets) > 1 {
		return false
	}
	if strings.Compare(strings.ToUpper(colCharsets[0]), c.GetTableCharset()) == 0 {
		return true
	}
	return false
}

// NameCheck TODO
func NameCheck(name string, mysqlVersion string) (etypesli, charsli []string) {
	reservesmap := getKewords(mysqlVersion)
	etypesli = []string{}
	charsli = []string{}
	if _, ok := reservesmap[name]; ok {
		etypesli = append(etypesli, "Keyword_exception")
		charsli = append(charsli, fmt.Sprintf("。库表名中包含了MySQL关键字: %s。请避免使用这些关键字！", name))
	}
	if regexp.MustCompile(`[￥$!@#%^&*()+={}\[\];:'"<>,.?/\\| ]`).MatchString(name) {
		chars := regexp.MustCompile(`[￥$!@#%^&*()+={}\[\];:'"<>,.?/\\| ]`).FindAllString(name, -1)
		etypesli = append(etypesli, "special_char")
		charsli = append(charsli, fmt.Sprintf("。库表名中包含以下特殊字符: %s。请避免在库表名称中使用这些特殊字符！", chars))
	}
	if regexp.MustCompile(`^[_]`).MatchString(name) {
		etypesli = append(etypesli, "first_char_exception")
		charsli = append(charsli, "。首字符不规范，请使用尽量字母或数字作为首字母")
	}
	return etypesli, charsli
}

func getKewords(mysqlVersion string) (keywordsmap map[string]string) {
	var keysli []string
	switch mysqlVersion {
	case "mysql5.6":
		keysli = MySQL56_KEYWORD
	case "mysql5.7":
		keysli = MySQL57_KEYWORD
	case "mysql8.0":
		keysli = MySQL80_KEYWORD
	default:
		keysli = ALL_KEYWORD
	}
	keywordsmap = map[string]string{}
	for _, key := range keysli {
		keywordsmap[key] = ""
	}
	return keywordsmap
}
