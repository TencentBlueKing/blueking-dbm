package main

import (
	"encoding/json"
	"fmt"
	"strings"

	"bk-dbconfig/internal/pkg/errno"
	"bk-dbconfig/internal/repository/model"
	"bk-dbconfig/pkg/constvar"
	"bk-dbconfig/pkg/core/config"
	"bk-dbconfig/pkg/util/crypt"

	"github.com/jinzhu/copier"
	"github.com/manifoldco/promptui"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"gorm.io/gorm"
)

var queryCmd = &cobra.Command{
	Use:   "query",
	Short: "query sensitive values such as password",
	Long:  `query sensitive values such as password, may use with --decrypt`,
	RunE: func(cmd *cobra.Command, args []string) error {
		confItems := make([]*ConfItemsResp, 0)
		var err error
		decrypt := config.GetBool("decrypt")
		// 查询密码解密 key 优先从命令行 old-key 获取，如果为空，则从配置文件 encrypt.keyPrefix 获取
		keyPrefix := config.GetString("old-key")
		if keyPrefix == "" {
			keyPrefix = config.GetString("encrypt.keyPrefix")
		}
		BkBizId := config.GetInt("bk-biz-id")
		if BkBizId == 0 {
			fmt.Printf("query plat's default config values(tb_config_name_def) using key=%s\n", keyPrefix)
			confItems, err = queryEncryptConfNames(decrypt, keyPrefix, model.DB.Self)
		} else {
			fmt.Printf("query bk_biz_id=%d config values (tb_config_node) using key=%s\n", BkBizId, keyPrefix)
			confItems, err = queryEncryptConfValues(decrypt, keyPrefix, model.DB.Self)
		}
		var jsonBytes []byte
		jsonBytes, _ = json.Marshal(confItems)
		fmt.Printf("\n%+v\n", string(jsonBytes))

		if err != nil {
			return err
		}
		return nil
	},
}

var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "update password with new encrypt key. you should backup it with query command",
	Long:  `update password with new encrypt key, may use with --old-key xxx --new-key yyy`,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		var confItems []*ConfItemsResp
		var rowsAffected int64
		// 旧 key 从命令行参数 --old-key 获取
		// 新 key 会优先从从命令参数 --new-key 获取，如果为空，则从配置文件获取 encrypt.keyPrefix
		oldKeyPrefix := config.GetString("old-key")
		newKeyPrefix := config.GetString("new-key")
		if newKeyPrefix == "" {
			newKeyPrefix = config.GetString("encrypt.keyPrefix")
		}
		if oldKeyPrefix == newKeyPrefix {
			return errors.Errorf("old key and new key is the same: %s", oldKeyPrefix)
		}
		BkBizId := config.GetInt("bk-biz-id")
		if BkBizId == 0 {
			fmt.Printf("query plat's default config values(tb_config_name_def) using key=%s\n", oldKeyPrefix)
			confItems, err = queryEncryptConfNames(true, oldKeyPrefix, model.DB.Self)
			if err != nil {
				return err
			}
			if err = updateDefaultValue(newKeyPrefix, confItems); err != nil {
				return err
			}
			fmt.Printf("update plat's default config values(tb_config_name_def), Count:%d\n", len(confItems))
			promptRes := runPrompt(newKeyPrefix, oldKeyPrefix)
			if promptRes == "y" {
				rowsAffected, err = updateDbEncryptDefaultValue(confItems, model.DB.Self)
			} else {
				fmt.Println("quit")
			}
		} else {
			fmt.Printf("query bk_biz_id=%d config values (tb_config_node) using key=%s\n", BkBizId, oldKeyPrefix)
			confItems, err = queryEncryptConfValues(true, oldKeyPrefix, model.DB.Self)
			if err != nil {
				return err
			}
			if err = updateConfValue(newKeyPrefix, confItems); err != nil {
				return err
			}
			fmt.Printf("update bk_biz_id=%d config values (tb_config_node) Count:%d\n", BkBizId, len(confItems))
			promptRes := runPrompt(newKeyPrefix, oldKeyPrefix)
			if promptRes == "y" {
				rowsAffected, err = updateDbEncryptConfValues(confItems, model.DB.Self)
			} else {
				fmt.Println("quit")
			}
		}
		fmt.Printf("rowsAffected:%d\n", rowsAffected)
		return err
	},
}

func runPrompt(newKey, oldKey string) string {
	prompt := promptui.Prompt{
		Label:     fmt.Sprintf("Are you sure to update key with new=%s, old=%s ", newKey, oldKey),
		IsConfirm: true,
		Default:   "N",
	}
	promptRes, _ := prompt.Run()
	return strings.ToLower(promptRes)
}

// ConfItemsResp copied from model.ConfigNameDefModel
type ConfItemsResp struct {
	ID           uint64 `json:"id"`
	Namespace    string `json:"namespace"`
	ConfType     string `json:"conf_type"`
	ConfFile     string `json:"conf_file"`
	BkBizId      string `json:"bk_biz_id"`
	ConfName     string `json:"conf_name"`
	ValueDefault string `json:"value_default"`
	ValueType    string `json:"value_type"`
	ValueTypeSub string `json:"value_type_sub"`
	//ValueAllowed string `json:"value_allowed"`
	FlagEncrypt int8 `json:"flag_encrypt"`
	//FlagLocked  int8 `json:"flag_locked"`
	//FlagStatus   int8   `json:"flag_status"`

	ConfValue  string `json:"conf_value"`
	LevelName  string `json:"level_name"`
	LevelValue string `json:"level_value"`

	// DecryptValue decrypted from ValueDefault or ConfValue
	DecryptValue string `json:"decrypt_value"`
}

func (r *ConfItemsResp) String() string {
	return fmt.Sprintf("{ID:%d Namespace:%s ConfType:%s ConfFile:%s BkBizId:%s ConfName:%s Level:%s=%s, "+
		"ValueDefault:%s ConfValue:%s DecryptValue:%s}",
		r.ID, r.Namespace, r.ConfType, r.ConfFile, r.BkBizId, r.ConfName, r.LevelName, r.LevelValue,
		r.ValueDefault, r.ConfValue, r.DecryptValue)
}

func queryEncryptConfNames(decrypt bool, keyPrefix string, db *gorm.DB) ([]*ConfItemsResp, error) {
	confNames := make([]*model.ConfigNameDefModel, 0)
	sqlRes := db.Model(model.ConfigNameDefModel{}).
		Select("id", "namespace", "conf_type", "conf_file", "conf_name", "value_default").
		Where("flag_encrypt = 1 and value_default not like '{{%'")
	if namespace := config.GetString("namespace"); namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if confType := config.GetString("conf-type"); confType != "" {
		sqlRes = sqlRes.Where("conf_type = ?", confType)
	}
	if confFile := config.GetString("conf-file"); confFile != "" {
		sqlRes = sqlRes.Where("conf_file = ?", confFile)
	}
	if names := config.GetStringSlice("conf-name"); len(names) != 0 {
		sqlRes = sqlRes.Where("conf_name in ?", names)
	}

	var err error
	if err = sqlRes.Find(&confNames).Error; err != nil {
		return nil, err
	}
	confItems := make([]*ConfItemsResp, 0)
	var errDecrypt bool
	for _, cn := range confNames {
		decryptValue := ""
		if decrypt {
			key := fmt.Sprintf("%s%s", keyPrefix, constvar.BKBizIDForPlat)
			decryptValue, err = crypt.DecryptString(cn.ValueDefault, key, constvar.EncryptEnableZip)
			if err != nil {
				fmt.Printf("error %s: %+v\n", err.Error(), cn)
				errDecrypt = true
				continue
			}
		}
		var one = &ConfItemsResp{}
		copier.Copy(one, cn)
		one.DecryptValue = decryptValue
		confItems = append(confItems, one)
	}
	if errDecrypt {
		return confItems, errno.ErrDecryptValue
	}

	return confItems, nil
}

func queryEncryptConfValues(decrypt bool, keyPrefix string, db *gorm.DB) ([]*ConfItemsResp, error) {
	confItems := make([]*model.ConfigModel, 0)
	sqlRes := db.Model(model.ConfigModel{}).
		Select("id", "namespace", "conf_type", "conf_file", "bk_biz_id",
			"conf_name", "conf_value", "level_name", "level_value").
		Where("conf_value like '**%'")
	if namespace := config.GetString("namespace"); namespace != "" {
		sqlRes = sqlRes.Where("namespace = ?", namespace)
	}
	if confType := config.GetString("conf-type"); confType != "" {
		sqlRes = sqlRes.Where("conf_type = ?", confType)
	}
	if confFile := config.GetString("conf-file"); confFile != "" {
		sqlRes = sqlRes.Where("conf_file = ?", confFile)
	}
	BkBizId := config.GetInt("bk-biz-id")
	if BkBizId != -1 { // bk-biz-id(bk_biz_id) = -1 means query all
		sqlRes = sqlRes.Where("bk_biz_id = ?", BkBizId)
	} else if BkBizId == 0 {
		return nil, errors.Errorf("bk_biz_id cannot be 0 when quering tb_config_node")
	}

	if names := config.GetStringSlice("conf-name"); len(names) != 0 {
		sqlRes = sqlRes.Where("conf_name in ?", names)
	}

	var err error
	if err = sqlRes.Find(&confItems).Error; err != nil {
		return nil, err
	}

	confValues := make([]*ConfItemsResp, 0)
	var errDecrypt bool
	for _, cn := range confItems {
		decryptValue := ""
		if decrypt {
			key := fmt.Sprintf("%s%s", keyPrefix, cn.LevelValue)
			decryptValue, err = crypt.DecryptString(cn.ConfValue, key, constvar.EncryptEnableZip)
			if err != nil {
				fmt.Printf("error %s: %+v\n", err.Error(), cn)
				errDecrypt = true
				continue
			}
		}
		var one = &ConfItemsResp{}
		copier.Copy(one, cn)
		one.DecryptValue = decryptValue
		confValues = append(confValues, one)
	}
	if errDecrypt {
		return confValues, errno.ErrDecryptValue
	}
	return confValues, nil
}

// updateConfValue 更新 confItems ConfValue
func updateConfValue(keyPrefix string, confItems []*ConfItemsResp) error {
	for _, conf := range confItems {
		newKey := fmt.Sprintf("%s%s", keyPrefix, conf.LevelValue)
		newValue, err := crypt.EncryptString(conf.DecryptValue, newKey, constvar.EncryptEnableZip)
		if err != nil {
			return errors.Wrapf(err, "%+v", conf)
		}
		fmt.Printf("%d %s,%s,%s,%s,%s=%s:\t%s\told=%s,new=%s\n",
			conf.ID, conf.Namespace, conf.ConfType, conf.ConfFile, conf.BkBizId, conf.LevelName, conf.LevelValue,
			conf.DecryptValue, conf.ConfValue, newValue)
		conf.ConfValue = newValue // 使用新的替代旧的
	}
	return nil
}

// updateDefaultValue 更新 confItems ValueDefault
func updateDefaultValue(keyPrefix string, confItems []*ConfItemsResp) error {
	newKey := fmt.Sprintf("%s%s", keyPrefix, constvar.BKBizIDForPlat)
	for _, conf := range confItems {
		newValue, err := crypt.EncryptString(conf.DecryptValue, newKey, constvar.EncryptEnableZip)
		if err != nil {
			return errors.Wrapf(err, "%+v", conf)
		}
		fmt.Printf("id=%d %s,%s,%s,%s,%s=%s:\t%s\told=%s,new=%s\n",
			conf.ID, conf.Namespace, conf.ConfType, conf.ConfFile, conf.BkBizId, "bk_biz_id", "0",
			conf.DecryptValue, conf.ValueDefault, newValue)
		conf.ValueDefault = newValue // 使用新的替代旧的
	}
	return nil
}

// updateDbEncryptDefaultValue 更新 db
// confItems ValueDefault 中是新的已经加密过的值
func updateDbEncryptDefaultValue(confItems []*ConfItemsResp, db *gorm.DB) (int64, error) {
	var err error
	var rowsAffected int64
	err = db.Transaction(func(tx *gorm.DB) error {
		for _, conf := range confItems {
			updateVal := tx.Model(model.ConfigNameDefModel{}).Where("id = ?", conf.ID).
				UpdateColumn("value_default", conf.ValueDefault)
			if updateVal.Error != nil {
				return errors.Wrapf(updateVal.Error, "%+v", conf)
			}
			if updateVal.RowsAffected != 1 {
				return errors.Errorf("expect 1 row affected, but got %d: %+v", updateVal.RowsAffected, conf)
			} else {
				rowsAffected += updateVal.RowsAffected
			}
		}
		return nil
	})
	return rowsAffected, err
}

// updateDbEncryptConfValues 更新 db
// confItems ConfValue 中是新的已经加密过的值
func updateDbEncryptConfValues(confItems []*ConfItemsResp, db *gorm.DB) (int64, error) {
	var rowsAffected int64
	err := db.Transaction(func(tx *gorm.DB) error {
		for _, conf := range confItems {
			updateVal := tx.Model(model.ConfigModel{}).Where("id = ?", conf.ID).
				UpdateColumn("conf_value", conf.ConfValue)
			if updateVal.Error != nil {
				return errors.Wrapf(updateVal.Error, "%+v", conf)
			}
			if updateVal.RowsAffected != 1 {
				return errors.Errorf("expect 1 row affected, but got %d: %+v", updateVal.RowsAffected, conf)
			} else {
				rowsAffected += updateVal.RowsAffected
			}
		}
		return nil
	})
	return rowsAffected, err
}
