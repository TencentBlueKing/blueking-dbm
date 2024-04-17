package service

import (
	"dnsReload/api"
	"dnsReload/config"
	"dnsReload/dao"
	"dnsReload/logger"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"strings"
	"sync"
)

var (
	wg      sync.WaitGroup
	errChan chan string
)

// zone文件生成规则
func getZoneFileName(d dao.TbDnsBase) string {
	domain := strings.Trim(strings.TrimSpace(strings.ToLower(d.DomainName)), ".")
	t := strings.Split(domain, ".")
	// 取后面三个字段作为zone name
	if len(t) <= 3 || !strings.HasSuffix(domain, "db") {
		return domain
	}
	beginIndex := len(t) - 3
	return strings.Join(t[beginIndex:], ".")
}

// 生成zone文件
func makeZoneFile(d dao.TbDnsBase, head string) string {
	if head == "" {
		head = `$TTL    6
@       IN      SOA     db.        root.db.   (
        2012011601      ; Serial
        600             ; Refresh
        14400           ; Retry
        7200            ; Expire
        900     )       ; minimum`
	}

	domain := strings.TrimSpace(strings.ToLower(d.DomainName))
	ip := strings.TrimSpace(d.Ip)
	return fmt.Sprintf("%s\n@               IN      NS    %s\n%s    IN    A    %s",
		head, domain, domain, ip)
}

// 替换forward ip
func replaceForwardIps(forwardIp string) error {
	namedFileTpl := config.GetConfig("options_named_file_tpl")
	content, err := ioutil.ReadFile(namedFileTpl)
	if err != nil {
		logger.Error.Printf("read named tpl file error [%+v]", err)
		return err
	}
	newContent := strings.ReplaceAll(string(content), "FORWARD_IPS", forwardIp)

	// 先写进临时文件，最后再替换。不然如果遇到半路失败的情况，会覆盖原有文件
	namedFile := config.GetConfig("options_named_file") + "_tmp"
	return ioutil.WriteFile(namedFile, []byte(newContent), 0666)
}

// 替换zone_config配置
func replaceZoneInfo(zoneNamedInfo string) error {
	tmpFile := config.GetConfig("options_named_file") + "_tmp"
	namedFile := config.GetConfig("options_named_file")
	content, err := ioutil.ReadFile(tmpFile)
	if err != nil {
		logger.Error.Printf("read tmp file error [%+v]", err)
		return err
	}
	newContent := strings.ReplaceAll(string(content), "ZONES_CONFIG", zoneNamedInfo)
	err = ioutil.WriteFile(tmpFile, []byte(newContent), 0666)
	if err != nil {
		logger.Error.Printf("write zones_config to tmp file error [%+v]", err)
		return err
	}

	// 能走到这里，说明配置文件生成过程中没遇到问题，可以替换了
	err = os.Rename(tmpFile, namedFile)
	if err != nil {
		logger.Error.Printf("rename named file error [%+v]", err)
		return err
	}
	return nil
}

func writeZoneName(fileName, fileContent string) {
	err := ioutil.WriteFile(fileName, []byte(fileContent), 0666)
	if err != nil {
		errChan <- err.Error()
	}
	wg.Done()
}

// 执行flush命令
func rndcReload() error {
	rndc := config.GetConfig("rndc")
	var cmd *exec.Cmd
	// server reload successful
	cmd = exec.Command(rndc, "reload")
	_, err := cmd.Output()
	if err != nil {
		logger.Error.Printf("rndc reload error [%+v]", err)
		return err
	}
	logger.Info.Printf("rndc reload success...")

	cmd = exec.Command(rndc, "flush")
	_, err = cmd.Output()
	if err != nil {
		logger.Error.Printf("rndc flush error [%+v]", err)
		return err
	}
	logger.Info.Printf("rndc flush success...")

	return nil
}

// checkReload 判断是否需要reload
func checkReload() bool {
	flushSwitch := config.GetConfig("flush_switch")
	return flushSwitch == "true"
}

// Reload 整个流程
func Reload(localIp string) error {
	logger.Info.Printf("reload begin...")
	defer logger.Info.Printf("reload end...")
	if !checkReload() {
		logger.Warning.Printf("flush_switch not is 1. needn't do reload")
		return nil
	}

	forwardIp := api.QueryForwardIp(localIp)
	if forwardIp == "" {
		logger.Warning.Printf("%s forwardIp is empty.. you should to set on config file[forward_ip]", localIp)
	} else {
		err := replaceForwardIps(forwardIp)
		if err != nil {
			logger.Error.Printf("replace forward ips error [%+v]", err)
			return err
		}
	}

	domainList, err := api.QueryAllDomainPost()
	if err != nil {
		logger.Error.Printf("query domain info error [%+v]", err)
		return err
	}

	if len(domainList) == 0 {
		logger.Warning.Printf("domainList len is 0. skip this update.", len(domainList))
		return nil
	}

	zoneFileMap := make(map[string]string)
	zoneNamedInfo := ""
	zoneDir := config.GetConfig("zone_dir_path")
	for _, data := range domainList {
		zoneName := getZoneFileName(data)
		if zoneName == "" {
			logger.Error.Printf("%s get zone file name is empty!!!", data.DomainName)
		}
		if _, _ok := zoneFileMap[zoneName]; !_ok {
			zoneNamedInfo = fmt.Sprintf("%s\n\nzone \"%s\" {\n        type master;\n        file \"%s\";\n};",
				zoneNamedInfo, zoneName, zoneDir+zoneName)
		}
		zoneFileMap[zoneName] = makeZoneFile(data, zoneFileMap[zoneName])
	}

	if len(zoneFileMap) == 0 {
		logger.Warning.Printf("zoneFileMap len is 0. skip this update.", len(zoneFileMap))
		return nil
	}

	wg = sync.WaitGroup{}
	wg.Add(len(zoneFileMap))
	logger.Info.Printf("zoneFileMap len is %d", len(zoneFileMap))
	for fn, fc := range zoneFileMap {
		go writeZoneName(zoneDir+fn, fc)
	}

	errMsg := ""
	errChan = make(chan string, 100)
	go func() {
		for msg := range errChan {
			if msg == "" {
				break
			}
			logger.Warning.Printf(msg)
			errMsg += "\n" + msg
		}
	}()

	wg.Wait()
	errChan <- ""

	if errMsg != "" {
		return fmt.Errorf(errMsg)
	}

	// 更新named.conf文件
	if err := replaceZoneInfo(zoneNamedInfo); err != nil {
		logger.Error.Printf("replaceZoneInfo error[%+v]", err)
		return err
	}

	// 触发rndc reload
	if err := rndcReload(); err != nil {
		logger.Error.Printf("rndc reload error [%+v]", err)
		return err
	}

	return nil
}
