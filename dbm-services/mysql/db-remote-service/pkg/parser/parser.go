// Package parser sql解析
package parser

// ParseQueryBase query result base field
type ParseQueryBase struct {
	QueryId   int    `json:"query_id"`
	Command   string `json:"command"`
	ErrorCode int    `json:"error_code"`
	ErrorMsg  string `json:"error_msg"`
}

//// ParseResult parse result
//type ParseResult struct {
//	Result          []*ParseQueryBase `json:"result"`
//	MinMySQLVersion int               `json:"min_mysql_version"`
//	MaxMySQLVersion int               `json:"max_my_sql_version"`
//}

//// Parse parser impl
//func Parse(payLoad string) (*ParseResult, error) {
//	tempDir, err := os.MkdirTemp("", uuid.New().String())
//	if err != nil {
//		return nil, err
//	}
//	defer func() {
//		_ = os.RemoveAll(tempDir)
//	}()
//
//	inputFile, err := os.CreateTemp(tempDir, "tmp_input_")
//	if err != nil {
//		return nil, err
//	}
//	defer func() {
//		_ = inputFile.Close()
//	}()
//
//	_, err = inputFile.WriteString(payLoad)
//	if err != nil {
//		return nil, err
//	}
//
//	var stdout, stderr bytes.Buffer
//	cmd := exec.Command(
//		config.RuntimeConfig.ParserBin,
//		"--sql-file", inputFile.Name(),
//		"--output-path", tempDir,
//	)
//	cmd.Stdout = &stdout
//	cmd.Stderr = &stderr
//
//	err = cmd.Run()
//	if err != nil {
//		return nil, errors.Wrap(err, stderr.String())
//	}
//
//	output, err := os.ReadFile(path.Join(tempDir, "tmysqlparse_out.json"))
//	if err != nil {
//		return nil, err
//	}
//
//	var res ParseResult
//	err = json.Unmarshal(output, &res)
//	if err != nil {
//		return nil, err
//	}
//
//	return &res, nil
//}
