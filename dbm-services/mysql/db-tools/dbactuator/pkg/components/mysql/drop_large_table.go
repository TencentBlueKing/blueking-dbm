package mysql

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"fmt"
)

// DropLargeTableComp TODO
type DropLargeTableComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       DropTableParam           `json:"extend"`
}

// DropTableParam godoc
// 1. show create table
// 2. rename table, create table
// 3. 做硬链接
// 4. drop table
// 5. 删除硬链和原始文件
type DropTableParam struct {
	Database   string   `json:"database" validate:"required"`
	Tables     []string `json:"tables" validate:"required"`
	LargeTable bool     `json:"large_table"`
	// 每秒删除速度 MB/s
	BWLimitMB int `json:"bwlimit_mb"`
	// 超过多少 MB 算大文件，大文件采用 trunc 限速删除
	LargeTableSizeMB int `json:"large_table_size_mb"`
	// 是否保留表结构，相当于 truncate table
	KeepSchema bool `json:"keep_schema"`

	// "table1"
	fileList map[string][]*linkFiles
}

type linkFiles struct {
	srcFile  string
	destFile string
}

// select @@datadir
// select SPACE,NAME,FILE_SIZE from INNODB_SYS_TABLESPACES where NAME like 'query_analyzer/%'
// query_analyzer/query_history#P#p202206 .ibd
//

func (d *DropTableParam) dropInnodbTable() error {
	// innodb_file_per_table

	for _, fileList := range d.fileList {
		for _, file := range fileList {
			file.destFile = fmt.Sprintf("%s.__drop__", file.srcFile)
			// osutil.MakeHardLink(file.srcFile, file.destFile)
			// osutil.TruncateFile(file.srcFile, d.BWLimit)
		}
	}

	return nil
}

func dropTokudbTable() error {
	return nil
}

func dropMyisamTable() error {
	return nil
}

func dropRocksdbTable() error {
	return nil
}
