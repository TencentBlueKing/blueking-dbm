package privcheck

import (
	"bufio"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/reportlog"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/privcheck/internal/checker"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"fmt"
	"io/fs"
	"log/slog"
	"os"
	"path/filepath"
	"regexp"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var name = "priv-check"

type Checker struct {
	db *sqlx.DB
	az *checker.Analyzer
}

type reportType struct {
	BkBizId       int       `json:"bk_biz_id"`
	BkCloudId     int       `json:"bk_cloud_id"`
	ClusterDomain string    `json:"cluster_domain"`
	MachineType   string    `json:"machine_type"`
	Ip            string    `json:"ip"`
	Port          int       `json:"port"`
	ReportTime    time.Time `json:"report_time"`
	*checker.PrivErrorInfo
}

func (c *Checker) Run() (msg string, err error) {
	//privs, err := c.showAllPrivileges()
	//if err != nil {
	//	slog.Error("show all privs", slog.String("err", err.Error()))
	//	return "", err
	//}

	privs, err := c.readPrivBackupFile()
	if err != nil {
		slog.Error("read backup file", slog.String("err", err.Error()))
		return "", err
	}

	slog.Info("priv-check read priv success")

	for _, priv := range privs {
		c.az.AddPrivSQLString(priv)
	}

	slog.Info("init az finished")

	report := c.az.Check(true)

	slog.Info("check finished")

	privCheckReportBaseDir := filepath.Join(cst.DBAReportBase, "mysql/privcheck")
	err = os.MkdirAll(privCheckReportBaseDir, os.ModePerm)
	if err != nil {
		slog.Error("create priv check report dir", slog.String("err", err.Error()))
		return "", err
	}

	resultReport, err := reportlog.NewReporter(
		privCheckReportBaseDir,
		fmt.Sprintf("report_%d.log", config.MonitorConfig.Port),
		nil,
	)
	if err != nil {
		slog.Error("create priv check report", slog.String("err", err.Error()))
		return "", err
	}
	reportTs := cmutil.TimeToSecondPrecision(time.Now())

	for _, r := range report {
		resultReport.Println(reportType{
			BkBizId:       config.MonitorConfig.BkBizId,
			BkCloudId:     *config.MonitorConfig.BkCloudID,
			ClusterDomain: config.MonitorConfig.ImmuteDomain,
			MachineType:   config.MonitorConfig.MachineType,
			Ip:            config.MonitorConfig.Ip,
			Port:          config.MonitorConfig.Port,
			ReportTime:    reportTs,
			PrivErrorInfo: r,
		})
	}

	return "", nil
}

func (c *Checker) readPrivBackupFile() (privs []string, err error) {
	dbBackupBaseDirs := []string{"/data/dbbak", "/data1/dbbak"}
	filePattern := regexp.MustCompile(
		fmt.Sprintf(
			`^.*_%s_%d_%s.*priv$`,
			config.MonitorConfig.Ip,
			config.MonitorConfig.Port,
			time.Now().Format("20060102"),
		),
	)

	var latestPrivFileEntry *fs.DirEntry
	var latestPrivFileInfo *fs.FileInfo
	var latestPrivFilePath string

	for _, dir := range dbBackupBaseDirs {
		err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
			if err != nil {
				return err
			}

			if !d.IsDir() && filePattern.MatchString(d.Name()) {
				info, err := d.Info()
				if err != nil {
					return err
				}
				if latestPrivFileEntry == nil || info.ModTime().After((*latestPrivFileInfo).ModTime()) {
					latestPrivFileEntry = &d
					latestPrivFileInfo = &info
					latestPrivFilePath = path
				}
			}

			return nil
		})
		if err != nil {
			return nil, err
		}
	}

	if latestPrivFileEntry != nil {
		f, err := os.Open(latestPrivFilePath)
		if err != nil {
			return nil, err
		}
		defer func() {
			_ = f.Close()
		}()

		scanner := bufio.NewScanner(f)
		for scanner.Scan() {
			privs = append(privs, scanner.Text())
		}
		if err := scanner.Err(); err != nil {
			return nil, err
		}
	}

	return privs, nil
}

func (c *Checker) showAllPrivileges() (privs []string, err error) {
	rows, err := c.db.Queryx(`SELECT user, host FROM mysql.user`)
	if err != nil {
		slog.Error("list user host", slog.String("err", err.Error()))
		return nil, errors.Wrap(err, "list user host")
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		var user, host string
		err = rows.Scan(&user, &host)
		if err != nil {
			slog.Error("scan user host", slog.String("err", err.Error()))
			return nil, errors.Wrap(err, "scan user host")
		}

		res, err := c.showPrivileges(user, host)
		if err != nil {
			slog.Error(
				"show one user grants",
				slog.String("user", user),
				slog.String("host", host),
				slog.String("err", err.Error()),
			)
		}

		privs = append(privs, res...)
	}
	if err := rows.Err(); err != nil {
		slog.Error("iterate user host", slog.String("err", err.Error()))
		return nil, errors.Wrap(err, "iterate user host")
	}

	return privs, nil
}

func (c *Checker) showPrivileges(user, host string) (privs []string, err error) {
	var version float32
	err = c.db.QueryRowx(`SELECT SUBSTRING_INDEX(@@version, ".", 2)`).Scan(&version)
	if err != nil {
		slog.Error("get version", slog.String("err", err.Error()))
		return nil, errors.Wrap(err, "get version")
	}

	if version > 5.5 {
		var createUserRes []string
		err = c.db.Select(
			&createUserRes,
			fmt.Sprintf(`SHOW CREATE USER '%s'@'%s'`, user, host),
		)
		if err != nil {
			slog.Error("get create user", slog.String("err", err.Error()))
			return nil, errors.Wrap(err, "get create user")
		}

		privs = append(privs, createUserRes...)
	}

	var grantsRes []string
	err = c.db.Select(
		&grantsRes,
		fmt.Sprintf(`SHOW GRANTS FOR '%s'@'%s'`, user, host),
	)
	if err != nil {
		slog.Error("get grants", slog.String("err", err.Error()))
		return nil, errors.Wrap(err, "get grants")
	}

	privs = append(privs, grantsRes...)
	return privs, nil
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db: cc.MySqlDB,
		az: checker.NewAnalyzer(),
	}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}
