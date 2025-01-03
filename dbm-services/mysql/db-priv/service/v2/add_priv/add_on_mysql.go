package add_priv

import (
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"

	"github.com/pkg/errors"
)

func (c *PrivTaskPara) addOnMySQL(
	clientIps []string, workingInstances map[int64][]string,
	accountAndRuleDetails *accountAndRule,
) (reports map[string][]string, err error) {
	reports = make(map[string][]string)
	var accountPSW service.MultiPsw
	err = json.Unmarshal([]byte(accountAndRuleDetails.TbAccount.Psw), &accountPSW)
	if err != nil {
		slog.Error("add on mysql",
			slog.String("psw", accountAndRuleDetails.TbAccount.Psw),
			slog.String("err", err.Error()),
		)
		return nil, err
	}
	slog.Info(
		"add on mysql",
		slog.String("psw", accountAndRuleDetails.TbAccount.Psw),
	)

	for _, dt := range accountAndRuleDetails.TbAccountRulesList {
		err := c.addOneDtOnMySQL(clientIps, workingInstances, accountAndRuleDetails, &accountPSW, dt, reports)
		if err != nil {
			slog.Error("add on mysql", slog.String("err", err.Error()))
			return nil, err
		}
		slog.Info(
			"add one dt on mysql finish",
			slog.Any("dt", dt),
		)
	}
	slog.Info(
		"add on mysql finish",
		slog.Any("reports", reports),
	)

	return reports, nil
}

/*
这个存储过程本身是有限制的
client ip 和 db list 最大只能 2000 长
db list不太可能超长, 因为前面把 dbname 单独循环了
client ip 有可能, 所以这里要切分下
*/
func (c *PrivTaskPara) addOneDtOnMySQL(
	clientIps []string,
	workingInstances map[int64][]string,
	accountAndRuleDetails *accountAndRule,
	psw *service.MultiPsw,
	dt *service.TbAccountRules,
	reports map[string][]string,
) error {
	var oneBatchClients []string
	for idx, ip := range clientIps {
		// 限长 100 代码会比较好些, 不往极限的 2000 搞
		oneBatchClients = append(oneBatchClients, ip)
		if len(oneBatchClients) > 100 || idx == len(clientIps)-1 {
			slog.Info("add one dt on mysql", slog.Any("one batch client", oneBatchClients))
			// 一次跑一批 client
			err := c.addOneDtOnMySQLForSplitClient(
				strings.Join(oneBatchClients, ","),
				workingInstances,
				accountAndRuleDetails,
				psw,
				dt,
				reports,
			)
			if err != nil {
				slog.Error("add on mysql", slog.String("err", err.Error()))
				return err
			}
			oneBatchClients = []string{}
		}
	}
	return nil
}

func (c *PrivTaskPara) addOneDtOnMySQLForSplitClient(
	clientIpsStr string,
	workingInstances map[int64][]string,
	accountAndRuleDetails *accountAndRule,
	psw *service.MultiPsw,
	dt *service.TbAccountRules,
	reports map[string][]string,
) error {
	for bkCloudId, workingInstanceAddrs := range workingInstances {
		slog.Info(
			"add on mysql call procedure",
			slog.Any("addrs", workingInstanceAddrs),
			slog.String("user", accountAndRuleDetails.TbAccount.User),
			slog.String("ipstr", clientIpsStr),
			slog.String("dbname", dt.Dbname),
			slog.String("psw", psw.Psw),
			slog.String("old psw", psw.OldPsw),
			slog.String("priv", dt.DmlDdlPriv),
			slog.String("global priv", dt.GlobalPriv),
		)
		drsRes, err := drs.RPCMySQL(
			bkCloudId,
			workingInstanceAddrs,
			[]string{
				fmt.Sprintf(
					`CALL infodba_schema.dba_grant('%s', '%s', '%s', '%s', '%s', '%s', '%s')`,
					accountAndRuleDetails.TbAccount.User,
					clientIpsStr,
					dt.Dbname,
					psw.Psw,
					psw.OldPsw,
					dt.DmlDdlPriv,
					dt.GlobalPriv,
				),
			},
			true,
			30,
		)
		// 调用 api 有问题, 比如 request body
		if err != nil {
			slog.Error("add on mysql", slog.String("err", err.Error()))
			return err
		}
		// 这里其实有个没检查, 不过应该不太可能
		// len(workingInstanceAddrs) == len(drsRes)
		slog.Info("add on mysql", slog.String("response", fmt.Sprintf("%+v", drsRes)))
		readOneDtRes(bkCloudId, drsRes, reports)
	}

	return nil
}

func readOneDtRes(bkCloudId int64, res []*drs.OneAddressResult, reports map[string][]string) {
	for _, r := range res {
		// 和 addr 建立连接之类的有问题
		// 这个错误应该收集起来
		if r.ErrorMsg != "" {
			err := errors.New(r.ErrorMsg)
			slog.Error(
				"add on mysql",
				slog.String("err", err.Error()),
				slog.String("addr", r.Address),
			)
			reports[r.Address] = []string{r.ErrorMsg}
			continue
		}
		readOneAddrRes(bkCloudId, r, reports)
	}
}

func readOneAddrRes(bkCloudId int64, r *drs.OneAddressResult, reports map[string][]string) {
	errMsg := r.CmdResults[0].ErrorMsg
	if errMsg == "" {
		return
	}

	if _, ok := reports[r.Address]; !ok {
		reports[r.Address] = make([]string, 0)
	}

	_, sqlStat, msgText, isException := internal.ParseMySQLErrStr(errMsg)
	if !isException {
		reports[r.Address] = append(reports[r.Address], msgText)
		return
	}

	switch sqlStat {
	case 32401:
		reports[r.Address] = append(reports[r.Address], msgText)
	case 32402:
		// 冲突检测错误
		readConflictReport(msgText, bkCloudId, r.Address, reports)
	default:
		reports[r.Address] = append(reports[r.Address], msgText)
	}
}

// 这个函数的所有错误都要收集了, 不能 return
func readConflictReport(uuid string, bkCloudId int64, addr string, reports map[string][]string) {
	r, err := drs.RPCMySQL(
		bkCloudId,
		[]string{addr},
		[]string{
			fmt.Sprintf(`SELECT * FROM infodba_schema.dba_grant_result WHERE id = '%s'`, uuid),
		},
		false,
		30,
	)
	if err != nil {
		slog.Error("add on mysql read conflict report", slog.String("err", err.Error()))
		reports[addr] = append(reports[addr], err.Error())
		return
	}

	if r[0].ErrorMsg != "" {
		slog.Error("add on mysql read conflict report", slog.String("err", r[0].ErrorMsg))
		reports[addr] = append(reports[addr], r[0].ErrorMsg)
		return
	}

	if r[0].CmdResults[0].ErrorMsg != "" {
		slog.Error("add on mysql read conflict report", slog.String("err", r[0].CmdResults[0].ErrorMsg))
		reports[addr] = append(reports[addr], r[0].CmdResults[0].ErrorMsg)
		return
	}

	for _, row := range r[0].CmdResults[0].TableData {
		dbname, ok := row["dbname"].(string)
		var msg string
		if ok {
			msg = fmt.Sprintf(
				`apply %s@%s on %s: %s`,
				row["username"], row["client_ip"], dbname, row["msg"],
			)
		} else {
			msg = fmt.Sprintf(
				`apply %s@%s: %s`,
				row["username"], row["client_ip"], row["msg"],
			)
		}

		slog.Error("add on mysql read conflict report", slog.String("msg", msg))
		reports[addr] = append(reports[addr], msg)
	}
	return
}
