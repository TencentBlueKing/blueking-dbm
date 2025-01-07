package main

import (
	"context"
	"database/sql"
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"slices"
	"strconv"
	"strings"
	"sync"

	"github.com/doug-martin/goqu/v9"
	_ "github.com/doug-martin/goqu/v9/dialect/mysql"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"golang.org/x/sync/errgroup"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/validate"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

/*
LOAD DATA [low_priority] [local] INFILE 'file_name txt' [REPLACE | IGNORE]
INTO TABLE tbl_name
[fields
[terminated by '\t']
[OPTIONALLY] enclosed by '"']
[escaped by '\' ]]
[lines terminated by '\n']
[ignore number lines]
[(col_name, )]

--low-priority
--dry-run  // 生成一个 batch-size, rollback
--concurrency xx // not work well with auto-commit-rows
--rows-per-second 100000
--disable-autocommit false
--disable-log-bin false
--insert-mode insert|replace|ignore
--fields-terminated-by ','
--fields-enclosed-by '"'
--lines-terminated-by '\n'
--ignore-lines N
--column-names col1,col2,col3
--column-types int,time,string,hex
--table-name dbx.table1
--batch-size 1000 // 1
--host xx --port xx --user xx --password xx --charset xx
--init-command 'set sql_mode=""'
--force
--lock-tables
--progress
--control-file xx
--result-file xxx
--load-data

rows_affected: xx, rows_failed: xx (x statements)
time_cost: xx s

control-file:
batch-size=xx
concurrency=yy
resume-from=0
*/

var rootCmd = &cobra.Command{
	Use:          "load-data-tosql",
	Short:        "load-data-tosql",
	Long:         "load-data-tosql replace mysqlbinlog",
	Version:      "1.0.0",
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) (err error) {
		return readCsvFile(viper.GetString("file"))
	},
}

func init() {
	// rootCmd
	rootCmd.PersistentFlags().String("file", "", "source csv file name")
	rootCmd.PersistentFlags().String("result-file", "",
		"output generated sql to file, if --concurrency>1, will use it as prefix")

	rootCmd.PersistentFlags().String("table-name", "", "format dbX.tableY")
	rootCmd.PersistentFlags().String("column-names", "", "column names list separated by comma")
	rootCmd.PersistentFlags().Bool("column-names-from-header", false,
		"get column names from csv header that is the first line")
	rootCmd.PersistentFlags().Bool("column-names-from-db", false,
		"get column names from table in target db")

	rootCmd.PersistentFlags().Int("ignore-lines", 0, "ignore number lines from beginning. "+
		"ignored lines will include the first line when using --column-names-from-header")
	rootCmd.PersistentFlags().Int("batch-size", 2, "rows insert per statement")
	rootCmd.PersistentFlags().Int("concurrency", 1, "threads or number of result-file to ingest")
	rootCmd.PersistentFlags().Bool("dry-run", false,
		"try run, only process one batch, and will not load-data to db")
	rootCmd.PersistentFlags().Bool("disable-log-bin", false, "disable sql_log_bin to ingest")
	rootCmd.PersistentFlags().Bool("disable-autocommit", false, "autocommit=1 by default, "+
		"set --disable-autocommit to ingest within one transaction")
	rootCmd.PersistentFlags().Bool("lock-table", false,
		"lock table will block all reads/writes to target table")
	rootCmd.PersistentFlags().Bool("load-data", false, "write data to mysql")
	rootCmd.PersistentFlags().String("fields-terminated-by", ",", "fields-terminated-by")

	rootCmd.PersistentFlags().StringP("host", "h", "", "connect host")
	rootCmd.PersistentFlags().IntP("port", "P", 3306, "connect port")
	rootCmd.PersistentFlags().StringP("user", "u", "root", "connect user name")
	rootCmd.PersistentFlags().StringP("password", "p", "", "connect password")
	rootCmd.PersistentFlags().String("charset", "utf8mb4", "connect default-character-set")
	rootCmd.PersistentFlags().StringP("socket", "S", "", "connect socket")

	_ = viper.BindPFlag("file", rootCmd.PersistentFlags().Lookup("file"))
	_ = viper.BindPFlag("result-file", rootCmd.PersistentFlags().Lookup("result-file"))
	_ = viper.BindPFlag("table-name", rootCmd.PersistentFlags().Lookup("table-name"))
	_ = viper.BindPFlag("column-names", rootCmd.PersistentFlags().Lookup("column-names"))
	_ = viper.BindPFlag("ignore-lines", rootCmd.PersistentFlags().Lookup("ignore-lines"))
	_ = viper.BindPFlag("column-names-from-header",
		rootCmd.PersistentFlags().Lookup("column-names-from-header"))
	_ = viper.BindPFlag("column-names-from-db", rootCmd.PersistentFlags().Lookup("column-names-from-db"))
	_ = viper.BindPFlag("batch-size", rootCmd.PersistentFlags().Lookup("batch-size"))
	_ = viper.BindPFlag("concurrency", rootCmd.PersistentFlags().Lookup("concurrency"))
	_ = viper.BindPFlag("dry-run", rootCmd.PersistentFlags().Lookup("dry-run"))
	_ = viper.BindPFlag("disable-log-bin", rootCmd.PersistentFlags().Lookup("disable-log-bin"))
	_ = viper.BindPFlag("disable-autocommit", rootCmd.PersistentFlags().Lookup("disable-autocommit"))
	_ = viper.BindPFlag("lock-table", rootCmd.PersistentFlags().Lookup("lock-table"))
	_ = viper.BindPFlag("load-data", rootCmd.PersistentFlags().Lookup("load-data"))
	_ = viper.BindPFlag("fields-terminated-by", rootCmd.PersistentFlags().Lookup("fields-terminated-by"))

	_ = viper.BindPFlag("host", rootCmd.PersistentFlags().Lookup("host"))
	_ = viper.BindPFlag("port", rootCmd.PersistentFlags().Lookup("port"))
	_ = viper.BindPFlag("user", rootCmd.PersistentFlags().Lookup("user"))
	_ = viper.BindPFlag("password", rootCmd.PersistentFlags().Lookup("password"))
	_ = viper.BindPFlag("charset", rootCmd.PersistentFlags().Lookup("charset"))
	_ = viper.BindPFlag("socket", rootCmd.PersistentFlags().Lookup("socket"))

	rootCmd.PersistentFlags().BoolP("help", "", false, "help for this command")
	_ = rootCmd.MarkFlagRequired("file")
	_ = rootCmd.MarkFlagRequired("table-name")
	rootCmd.MarkFlagsMutuallyExclusive("column-names", "column-names-from-db", "column-names-from-header")
	//rootCmd.MarkFlagsRequiredTogether("")
	//rootCmd.MarkFlagsRequiredTogether("host", "port", "user", "password")
}

type Options struct {
	DisableLogBin bool `mapstructure:"disable-log-bin"`
	// DisableAutocommit run in one connection
	DisableAutocommit bool `mapstructure:"disable-autocommit"`
	// LockTable run in one connection
	LockTable bool `mapstructure:"lock-table"`

	DryRun     bool   `mapstructure:"dry-run"`
	LoadData   bool   `mapstructure:"load-data"`
	ResultFile string `mapstructure:"result-file"`

	File                  string `mapstructure:"file" validate:"required"`
	TableName             string `mapstructure:"table-name" validate:"required"`
	ColumnNames           string `mapstructure:"column-names"`
	ColumnNamesFromHeader bool   `mapstructure:"column-names-from-header"`
	ColumnNamesFromDb     bool   `mapstructure:"column-names-from-db"`

	IgnoreLines int `mapstructure:"ignore-lines"`
	BatchSize   int `mapstructure:"batch-size" validate:"gte=1"`
	Concurrency int `mapstructure:"concurrency"`

	FieldsTerminatedBy string `mapstructure:"fields-terminated-by"`

	columnNames        []interface{}
	fieldsTerminatedBy rune
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func readCsvFile(filePath string) error {
	var opt Options
	err := viper.Unmarshal(&opt)
	if err != nil {
		return err
	}
	if err = validate.GoValidateTransError(opt, "mapstructure", false, false); err != nil {
		return err
	}

	if opt.DryRun {
		opt.DisableAutocommit = true
	}
	//replace := false
	var columnNames []interface{}
	tableName := opt.TableName
	if opt.ColumnNamesFromHeader && opt.IgnoreLines == 0 {
		opt.IgnoreLines = 1
	}

	if opt.DisableAutocommit && opt.Concurrency > 1 {
		return errors.Errorf("--disable-autocommit only work with --concurrency=1")
	}
	if opt.LockTable && opt.Concurrency > 1 {
		return errors.Errorf("--lock-table only work with --concurrency=1")
	}

	var writer io.WriteCloser
	var instance native.InsObject
	var dbWorker *native.DbWorker
	if opt.LoadData || opt.ColumnNamesFromDb {
		instance = native.InsObject{
			Host:    viper.GetString("host"),
			Port:    viper.GetInt("port"),
			User:    viper.GetString("user"),
			Pwd:     viper.GetString("password"),
			Charset: viper.GetString("charset"),
			Socket:  viper.GetString("socket"),
		}
		dbWorker, err = instance.Conn()
		if err != nil {
			return err
		}
	}
	if resultFile := viper.GetString("result-file"); resultFile == "" {
		writer = os.Stdout
	} else {
		outFile, err := os.OpenFile(resultFile, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0755)
		if err != nil {
			return err
		}
		writer = outFile
	}
	defer writer.Close()

	if opt.ColumnNames != "" {
		columnNames = lo.Map(strings.Split(opt.ColumnNames, ","), func(x string, index int) interface{} {
			return interface{}(strings.TrimSpace(x))
		})
	}

	inFile, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer inFile.Close()

	reader := csv.NewReader(inFile)
	//reader.InputOffset()
	sep := getSeparator(opt.FieldsTerminatedBy)
	if !slices.Contains([]rune{',', '\t'}, sep) {
		return errors.Errorf("--fields-terminated-by expect one character, bug got %s",
			viper.GetString("fields-terminated-by"))
	} else {
		reader.Comma = sep
	}
	//reader.LazyQuotes = true

	g, ctx := errgroup.WithContext(context.Background())
	var result sync.Map

	if opt.Concurrency > 0 {
		g.SetLimit(opt.Concurrency)
	} else {
		return errors.Errorf("invalid ingest concurrency value %d", opt.Concurrency)
	}

	sqlBuilder := goqu.Dialect("mysql")
	//db := goqu.New("mysql", mysqlDB) // db
	ds := sqlBuilder.Insert(tableName).Cols(columnNames...)
	batchCount := 0
	rowsCurrent := 0

	var processor OutputProcessor
	if opt.LoadData {
		processor = &LoadProcessor{
			dbConn: dbWorker.Db,
			opt:    &opt,
		}
	} else {
		processor = &PrintProcessor{
			writer: writer,
			opt:    &opt,
		}
	}

	if err = processor.HandleHeader(ctx); err != nil {
		return err
	}
	var dryRunSql string
	var linesIgnored int
	var lineNum int64

	var errChan = make(chan error, 1)
	errChan <- nil
	for {
		line, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			_ = processor.HandleFooter(err, ctx)
			if errors.Is(err, csv.ErrFieldCount) {
				return errors.WithMessagef(err, "expect %d but got %d", len(columnNames), len(line))
			}
			return err
		}
		lineNum += 1

		fieldValues := lo.Map(line, func(x string, index int) interface{} {
			return interface{}(x)
		})

		if lineNum == 1 { // the first line
			if opt.ColumnNamesFromHeader {
				// 把第一行作为列名
				columnNames = fieldValues
				reader.FieldsPerRecord = len(columnNames)
			}
			if opt.ColumnNamesFromDb && len(columnNames) == 0 {
				columns, err := getColumnNamesFromDb(tableName, dbWorker.Db)
				if err != nil {
					return errors.WithMessage(err, "get column names from db")
				}
				for _, col := range columns {
					columnNames = append(columnNames, col.ColName)
				}
			}
			if len(columnNames) == 0 {
				return errors.Errorf("not column names givien, use --column-names c1,c2 / " +
					"--column-names-from-header / --column-names-from-db as you need")
			}
			ds = sqlBuilder.Insert(tableName).Cols(columnNames...)

			if len(fieldValues) != len(columnNames) {
				return errors.Errorf("--column-names count %d does not match csv header %d",
					len(columnNames), len(fieldValues))
				// 只导入部分列
			}
			if opt.IgnoreLines > 0 {
				linesIgnored += 1
				continue
			}
		}
		if opt.IgnoreLines > linesIgnored {
			linesIgnored += 1
			continue
		}
		ds = ds.Vals(fieldValues)
		rowsCurrent += 1

		if rowsCurrent >= opt.BatchSize {
			batchCount += 1
			insertSQL, _, _ := ds.ToSQL()

			if opt.DryRun { // the first batch, dry-run
				dryRunSql = insertSQL
				break
			}
			// reset builder
			ds = sqlBuilder.Insert(tableName).Cols(columnNames...)
			rowsCurrent = 0

			select {
			case e := <-errChan:
				if e != nil {
					return e
				}
				//default:
			}

			g.Go(func() error {
				internalErr := processor.Process(insertSQL, ctx)
				errChan <- internalErr
				return internalErr
			})
		}
	}
	if opt.DryRun {
		err = processor.Process(dryRunSql, ctx)
		_ = processor.Process("ROLLBACK", ctx)
		return nil
	}
	if rowsCurrent > 0 { // the last batch
		if lastErr := <-errChan; lastErr != nil {
			fmt.Println("line", lineNum, "has error")
			return lastErr
		}

		batchCount += 1
		insertSQL, _, _ := ds.ToSQL()
		if err = processor.Process(insertSQL, ctx); err != nil {
			return err
		}
		return processor.HandleFooter(nil, ctx)
	}

	// 等待所有 goroutine 完成并返回第一个错误（如果有）
	if err := g.Wait(); err != nil {
		fmt.Printf("Encountered an error: %v\n", err)
	}

	// 所有 goroutine 都执行完成，遍历并打印成功的结果
	result.Range(func(key, value any) bool {
		//fmt.Printf("fetch url %s status %s\n", key, value)
		return true
	})

	return nil
}

func getColumnNamesFromDb(dbTable string, db *sql.DB) ([]native.TableColumnDef, error) {
	dbWorker := &native.DbWorker{
		Db: db,
	}
	dbName, tableName, err := cmutil.GetDbTableName(dbTable)
	if err != nil {
		return nil, err
	}
	columnsDef, err := native.GetTableColumnList(dbName, tableName, dbWorker)
	if err != nil {
		return nil, err
	}
	return columnsDef, nil
}

func getSeparator(sepString string) (sepRune rune) {
	sepString = `'` + sepString + `'`
	sepRunes, err := strconv.Unquote(sepString)
	if err != nil {
		// Single quote was used as separator. No idea why someone would want this, but it doesn't hurt to support it
		if err.Error() == "invalid syntax" {
			sepString = `"` + sepString + `"`
			sepRunes, err = strconv.Unquote(sepString)
			if err != nil {
				panic(err)
			}

		} else {
			panic(err)
		}
	}
	sepRune = ([]rune(sepRunes))[0]

	return sepRune
}
