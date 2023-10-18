package syntax_test

import (
	"bufio"
	"encoding/json"
	"io"
	"os"
	"testing"
)

type ParseQueryBase struct {
	Command         string `json:"command"`
	QueryString     string `json:"query_string,omitempty"`
	ErrorMsg        string `json:"error_msg,omitempty"`
	QueryId         int    `json:"query_id"`
	ErrorCode       int    `json:"error_code,omitempty"`
	MinMySQLVersion int    `json:"min_mysql_version"`
	MaxMySQLVersion int    `json:"max_my_sql_version"`
}

func Test_tmysqlparse(t *testing.T) {
	t.Log("starting ...")
	f, err := os.Open("/data/tmysqlparse_out.json")
	if err != nil {
		t.Logf("open file failed %s", err.Error())
		return
	}
	defer f.Close()
	reader := bufio.NewReader(f)
	for {
		line, _, err := reader.ReadLine()
		if err == io.EOF {
			break
		}
		var res ParseQueryBase
		if err = json.Unmarshal(line, &res); err != nil {
			t.Fatal(err)
			return
		}
		t.Log(res)
	}
	t.Log("ending ...")
}
