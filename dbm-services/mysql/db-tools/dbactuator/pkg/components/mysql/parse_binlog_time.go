package mysql

import (
	"encoding/json"
	"fmt"
	"path/filepath"

	"dbm-services/common/go-pubpkg/cmutil"
	binlogParser "dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/binlog-parser"
)

// BinlogTimeComp TODO
type BinlogTimeComp struct {
	Params BinlogTimeParam `json:"extend"`
}

// Example TODO
func (t *BinlogTimeComp) Example() interface{} {
	return &BinlogTimeComp{
		Params: BinlogTimeParam{
			BinlogDir:   "/data/dbbak",
			BinlogFiles: []string{"binlog20000.00001", "binlog20000.00002"},
			Format:      "json",
		},
	}
}

// BinlogTimeParam TODO
type BinlogTimeParam struct {
	BinlogDir   string   `json:"binlog_dir" validate:"required"`
	BinlogFiles []string `json:"binlog_files" validate:"required"`
	Format      string   `json:"format" enums:",json,dump"`
	parser      *binlogParser.BinlogParse
}

// Init TODO
func (t *BinlogTimeComp) Init() error {
	bp, err := binlogParser.NewBinlogParse("mysql", 0)
	if err != nil {
		return err
	}
	t.Params.parser = bp
	return nil
}

// Start TODO
func (t *BinlogTimeComp) Start() error {
	for _, f := range t.Params.BinlogFiles {
		filename := filepath.Join(t.Params.BinlogDir, f)
		if err := cmutil.FileExistsErr(filename); err != nil {
			fmt.Printf("%s: %v\n", filename, err)
			continue
		}
		if events, err := t.Params.parser.GetTime(filename, true, true); err != nil {
			fmt.Printf("%s: %v\n", filename, err)
		} else {
			b, _ := json.Marshal(events)
			fmt.Printf("%s: %s\n", filename, b)
		}
	}
	return nil
}
